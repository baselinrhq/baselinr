"""
Incremental planner that decides which tables to run, skip, or partially profile.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..config.schema import ProfileMeshConfig, TablePattern
from ..connectors.factory import create_connector
from ..events import EventBus, ProfilingSkipped
from .change_detection import ChangeSummary, build_change_detector
from .state import TableState, TableStateStore

logger = logging.getLogger(__name__)


@dataclass
class TableRunDecision:
    table: TablePattern
    action: str  # skip | full | partial | defer | sample
    reason: str
    changed_partitions: List[str] = field(default_factory=list)
    snapshot_id: Optional[str] = None
    estimated_cost: Optional[int] = None
    use_sampling: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IncrementalPlan:
    generated_at: datetime
    run_id: str
    decisions: List[TableRunDecision]

    def runnable_tables(self) -> List[TablePattern]:
        runnable = []
        for decision in self.decisions:
            if decision.action in ("full", "partial", "sample"):
                runnable.append(decision.table)
        return runnable

    def to_summary(self) -> Dict[str, Any]:
        counts = {
            "full": len([d for d in self.decisions if d.action == "full"]),
            "partial": len([d for d in self.decisions if d.action == "partial"]),
            "sample": len([d for d in self.decisions if d.action == "sample"]),
            "skip": len([d for d in self.decisions if d.action == "skip"]),
            "defer": len([d for d in self.decisions if d.action == "defer"]),
        }
        return {
            "generated_at": self.generated_at.isoformat(),
            "run_id": self.run_id,
            "counts": counts,
        }


class IncrementalPlanner:
    """Planner that applies change detection, scheduling, and cost guardrails."""

    def __init__(
        self,
        config: ProfileMeshConfig,
        state_store: Optional[TableStateStore] = None,
        event_bus: Optional[EventBus] = None,
    ):
        self.config = config
        self.event_bus = event_bus
        incremental_cfg = config.incremental

        self.state_store = state_store or TableStateStore(
            storage_config=config.storage,
            table_name=incremental_cfg.change_detection.metadata_table,
            retry_config=config.retry,
            create_tables=True,
        )
        self.connector = create_connector(config.source, config.retry, config.execution)
        self.change_detector = build_change_detector(
            config.source.type, self.connector, incremental_cfg
        )

    def get_tables_to_run(self, current_time: Optional[datetime] = None) -> IncrementalPlan:
        """Return the plan for the current tick."""
        now = current_time or datetime.now(timezone.utc)
        decisions: List[TableRunDecision] = []
        for table_pattern in self.config.profiling.tables:
            decision = self._decide_for_table(table_pattern, now)
            decisions.append(decision)
        plan = IncrementalPlan(
            generated_at=now,
            run_id=str(uuid.uuid4()),
            decisions=decisions,
        )
        return plan

    def _decide_for_table(self, table: TablePattern, now: datetime) -> TableRunDecision:
        incremental_cfg = self.config.incremental
        if not incremental_cfg.enabled:
            return TableRunDecision(table=table, action="full", reason="incremental_disabled")

        state = self.state_store.load_state(table.table, table.schema_)
        if not self._is_due(state, now):
            reason = "fresh_within_interval"
            self._emit_skip(table, reason, state)
            return TableRunDecision(table=table, action="skip", reason=reason)

        summary = self._summarize_changes(table, state)
        if state and summary.snapshot_id and summary.snapshot_id == state.snapshot_id:
            reason = "snapshot_match"
            self._emit_skip(table, reason, state)
            return TableRunDecision(
                table=table, action="skip", reason=reason, snapshot_id=summary.snapshot_id
            )

        cost_decision = self._check_costs(summary)
        if cost_decision:
            if cost_decision["should_run"]:
                action = cost_decision["action"]
                if action == "sample":
                    return TableRunDecision(
                        table=table,
                        action="sample",
                        reason=cost_decision["reason"],
                        snapshot_id=summary.snapshot_id,
                        estimated_cost=self._estimate_cost(summary),
                        use_sampling=True,
                        metadata=summary.metadata,
                    )
                if action == "full":
                    return TableRunDecision(
                        table=table,
                        action="full",
                        reason=cost_decision["reason"],
                        snapshot_id=summary.snapshot_id,
                        estimated_cost=self._estimate_cost(summary),
                        metadata=summary.metadata,
                    )
            else:
                action = cost_decision["action"]
                reason = cost_decision["reason"]
                self._emit_skip(
                    table, reason, state, snapshot_id=summary.snapshot_id, action=action
                )
                return TableRunDecision(
                    table=table,
                    action=action,
                    reason=reason,
                    snapshot_id=summary.snapshot_id,
                    estimated_cost=self._estimate_cost(summary),
                    metadata=summary.metadata,
                )

        if (
            incremental_cfg.partial_profiling.enabled
            and summary.changed_partitions
            and incremental_cfg.partial_profiling.allow_partition_pruning
        ):
            return TableRunDecision(
                table=table,
                action="partial",
                reason="changed_partitions_detected",
                changed_partitions=summary.changed_partitions,
                snapshot_id=summary.snapshot_id,
                estimated_cost=self._estimate_cost(summary),
                metadata=summary.metadata,
            )

        return TableRunDecision(
            table=table,
            action="full",
            reason="change_detected",
            snapshot_id=summary.snapshot_id,
            estimated_cost=self._estimate_cost(summary),
            metadata=summary.metadata,
        )

    def _is_due(self, state: Optional[TableState], now: datetime) -> bool:
        cfg = self.config.incremental.adaptive_scheduling
        if not cfg.enabled or not state or not state.last_profiled_at:
            return True
        priority_key = state.table_key.lower()
        custom_interval = cfg.priority_overrides.get(priority_key)
        interval_minutes = custom_interval or cfg.default_interval_minutes
        interval_minutes = min(
            max(interval_minutes, cfg.min_interval_minutes), cfg.max_interval_minutes
        )
        next_due = state.last_profiled_at + timedelta(minutes=interval_minutes)
        return now >= next_due

    def _summarize_changes(self, table: TablePattern, state: Optional[TableState]) -> ChangeSummary:
        previous_snapshot = state.snapshot_id if state else None
        try:
            return self.change_detector.summarize(table, previous_snapshot_id=previous_snapshot)
        except Exception as exc:
            logger.warning("Change detection failed for %s: %s", table.table, exc)
            return ChangeSummary(metadata={"error": str(exc)})

    def _estimate_cost(self, summary: ChangeSummary) -> Optional[int]:
        if summary.bytes_scanned is not None:
            return summary.bytes_scanned
        if summary.row_count is not None:
            # Assume 1KB per row as a loose heuristic
            return summary.row_count * 1024
        return None

    def _check_costs(self, summary: ChangeSummary) -> Optional[Dict[str, Any]]:
        cfg = self.config.incremental.cost_controls
        if not cfg.enabled:
            return None
        estimated_bytes = self._estimate_cost(summary)
        estimated_rows = summary.row_count
        if cfg.max_bytes_scanned and estimated_bytes and estimated_bytes > cfg.max_bytes_scanned:
            return self._cost_response(cfg, "bytes_cap_exceeded")
        if cfg.max_rows_scanned and estimated_rows and estimated_rows > cfg.max_rows_scanned:
            return self._cost_response(cfg, "rows_cap_exceeded")
        return None

    def _cost_response(self, cfg, reason: str):
        strategy = cfg.fallback_strategy
        if strategy == "sample":
            return {"action": "sample", "reason": reason, "should_run": True}
        if strategy == "defer":
            return {"action": "defer", "reason": reason, "should_run": False}
        return {"action": "full", "reason": reason, "should_run": True}

    def _emit_skip(
        self,
        table: TablePattern,
        reason: str,
        state: Optional[TableState],
        snapshot_id: Optional[str] = None,
        action: str = "skip",
    ):
        logger.info("Skipping %s.%s: %s", table.schema_ or "public", table.table, reason)
        self.state_store.record_decision(
            table_name=table.table,
            schema_name=table.schema_,
            decision=action,
            reason=reason,
            snapshot_id=snapshot_id,
            metadata={"previous_snapshot": state.snapshot_id if state else None},
        )
        if self.event_bus:
            self.event_bus.emit(
                ProfilingSkipped.create(
                    table=table.table,
                    schema=table.schema_,
                    reason=reason,
                    action=action,
                    snapshot_id=snapshot_id,
                )
            )
