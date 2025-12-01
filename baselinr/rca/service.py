"""
RCA Service for triggering and managing root cause analysis.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.engine import Engine

from ..events import AnomalyDetected, EventBus
from .analysis.root_cause_analyzer import RootCauseAnalyzer
from .models import RCAResult
from .storage import RCAStorage

logger = logging.getLogger(__name__)


class RCAService:
    """
    Service for managing RCA operations.

    Subscribes to anomaly detection events and triggers RCA automatically,
    or can be invoked manually via API.
    """

    def __init__(
        self,
        engine: Engine,
        event_bus: Optional[EventBus] = None,
        auto_analyze: bool = True,
        lookback_window_hours: int = 24,
        max_depth: int = 5,
        max_causes_to_return: int = 5,
        min_confidence_threshold: float = 0.3,
        enable_pattern_learning: bool = True,
    ):
        """
        Initialize RCA service.

        Args:
            engine: SQLAlchemy engine
            event_bus: Event bus for subscribing to anomalies
            auto_analyze: Automatically analyze anomalies when detected
            lookback_window_hours: Time window for finding causes
            max_depth: Maximum depth for lineage traversal
            max_causes_to_return: Maximum number of causes to return
            min_confidence_threshold: Minimum confidence to include a cause
            enable_pattern_learning: Whether to use pattern matching
        """
        self.engine = engine
        self.event_bus = event_bus
        self.auto_analyze = auto_analyze

        # Initialize storage
        self.storage = RCAStorage(engine)

        # Initialize analyzer
        self.analyzer = RootCauseAnalyzer(
            engine=engine,
            lookback_window_hours=lookback_window_hours,
            max_depth=max_depth,
            max_causes_to_return=max_causes_to_return,
            min_confidence_threshold=min_confidence_threshold,
            enable_pattern_learning=enable_pattern_learning,
        )

        # Subscribe to anomaly events if auto-analyze is enabled
        if auto_analyze and event_bus:
            self._subscribe_to_anomalies()

    def _subscribe_to_anomalies(self):
        """Subscribe to anomaly detection events."""
        if not self.event_bus:
            logger.warning("No event bus provided, cannot subscribe to anomalies")
            return

        def handle_anomaly(event: AnomalyDetected):
            """Handle anomaly detection event."""
            try:
                logger.info(f"Auto-analyzing anomaly in {event.table}.{event.column}")

                # Trigger RCA
                self.analyze_anomaly(
                    anomaly_id=event.metadata.get("anomaly_id", f"anomaly_{event.timestamp}"),
                    table_name=event.table,
                    anomaly_timestamp=event.timestamp,
                    schema_name=event.metadata.get("schema_name"),
                    column_name=event.column,
                    metric_name=event.metric,
                    anomaly_type=event.anomaly_type,
                )

            except Exception as e:
                logger.error(f"Error in auto-analysis: {e}")

        # Register handler
        self.event_bus.subscribe("AnomalyDetected", handle_anomaly)
        logger.info("RCA service subscribed to anomaly events")

    def analyze_anomaly(
        self,
        anomaly_id: str,
        table_name: str,
        anomaly_timestamp: datetime,
        database_name: Optional[str] = None,
        schema_name: Optional[str] = None,
        column_name: Optional[str] = None,
        metric_name: Optional[str] = None,
        anomaly_type: Optional[str] = None,
    ) -> RCAResult:
        """
        Analyze a specific anomaly.

        Args:
            anomaly_id: Unique identifier for the anomaly
            table_name: Table with the anomaly
            anomaly_timestamp: When the anomaly occurred
            database_name: Database name (for multi-database warehouses)
            schema_name: Schema name
            column_name: Column with anomaly
            metric_name: Metric that is anomalous
            anomaly_type: Type of anomaly

        Returns:
            RCAResult object
        """
        logger.info(f"Starting RCA for anomaly {anomaly_id}")

        try:
            # Perform analysis
            result = self.analyzer.analyze(
                anomaly_id=anomaly_id,
                table_name=table_name,
                anomaly_timestamp=anomaly_timestamp,
                database_name=database_name,
                schema_name=schema_name,
                column_name=column_name,
                metric_name=metric_name,
                anomaly_type=anomaly_type,
            )

            # Store result
            self.storage.write_rca_result(result)

            logger.info(
                f"RCA complete for {anomaly_id}, found {len(result.probable_causes)} causes"
            )

            return result

        except Exception as e:
            logger.error(f"Error analyzing anomaly {anomaly_id}: {e}")
            raise

    def get_rca_result(self, anomaly_id: str) -> Optional[RCAResult]:
        """
        Get stored RCA result for an anomaly.

        Args:
            anomaly_id: Anomaly ID

        Returns:
            RCAResult or None if not found
        """
        return self.storage.get_rca_result(anomaly_id)

    def reanalyze_anomaly(self, anomaly_id: str) -> Optional[RCAResult]:
        """
        Re-run RCA for an existing anomaly.

        Useful after new data is available or patterns have been learned.

        Args:
            anomaly_id: Anomaly ID to re-analyze

        Returns:
            Updated RCAResult or None if anomaly not found
        """
        # Get existing result to extract metadata
        existing_result = self.storage.get_rca_result(anomaly_id)

        if not existing_result:
            logger.warning(f"Cannot reanalyze: anomaly {anomaly_id} not found")
            return None

        # Re-run analysis with same parameters
        logger.info(f"Re-analyzing anomaly {anomaly_id}")

        # We need the original timestamp - try to get from events table
        from sqlalchemy import text

        query = text(
            """
            SELECT timestamp FROM baselinr_events
            WHERE event_id = :anomaly_id
            OR metadata LIKE :anomaly_pattern
            LIMIT 1
        """
        )

        anomaly_timestamp = datetime.utcnow()  # Default to now

        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    query,
                    {
                        "anomaly_id": anomaly_id,
                        "anomaly_pattern": f"%{anomaly_id}%",
                    },
                )
                row = result.fetchone()
                if row:
                    anomaly_timestamp = row[0]

        except Exception as e:
            logger.warning(f"Could not find original timestamp: {e}")

        # Perform re-analysis
        return self.analyze_anomaly(
            anomaly_id=anomaly_id,
            table_name=existing_result.table_name,
            anomaly_timestamp=anomaly_timestamp,
            schema_name=existing_result.schema_name,
            column_name=existing_result.column_name,
            metric_name=existing_result.metric_name,
        )

    def analyze_multiple_anomalies(
        self,
        anomalies: List[Dict[str, Any]],
    ) -> List[RCAResult]:
        """
        Analyze multiple related anomalies.

        Args:
            anomalies: List of anomaly dicts

        Returns:
            List of RCAResult objects
        """
        logger.info(f"Analyzing {len(anomalies)} anomalies")

        results = self.analyzer.analyze_multiple_anomalies(anomalies)

        # Store all results
        for result in results:
            try:
                self.storage.write_rca_result(result)
            except Exception as e:
                logger.error(f"Error storing result for {result.anomaly_id}: {e}")

        return results

    def dismiss_rca_result(self, anomaly_id: str, reason: Optional[str] = None):
        """
        Mark an RCA result as dismissed.

        Args:
            anomaly_id: Anomaly ID
            reason: Optional reason for dismissing
        """
        from sqlalchemy import text

        query = text(
            """
            UPDATE baselinr_rca_results
            SET rca_status = 'dismissed',
                metadata = :metadata
            WHERE anomaly_id = :anomaly_id
        """
        )

        try:
            with self.engine.connect() as conn:
                # Get existing metadata
                select_query = text(
                    """
                    SELECT metadata FROM baselinr_rca_results
                    WHERE anomaly_id = :anomaly_id
                """
                )
                result = conn.execute(select_query, {"anomaly_id": anomaly_id})
                row = result.fetchone()

                if row:
                    import json

                    metadata = json.loads(row[0]) if row[0] else {}
                    metadata["dismissed"] = {
                        "dismissed_at": datetime.utcnow().isoformat(),
                        "reason": reason,
                    }

                    conn.execute(
                        query,
                        {
                            "anomaly_id": anomaly_id,
                            "metadata": json.dumps(metadata),
                        },
                    )
                    conn.commit()

                    logger.info(f"Dismissed RCA result for {anomaly_id}")

        except Exception as e:
            logger.error(f"Error dismissing RCA result: {e}")

    def get_rca_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about RCA operations.

        Returns:
            Dictionary with statistics
        """
        from sqlalchemy import text

        stats = {
            "total_analyses": 0,
            "analyzed": 0,
            "dismissed": 0,
            "pending": 0,
            "avg_causes_per_anomaly": 0.0,
        }

        try:
            with self.engine.connect() as conn:
                # Count by status
                count_query = text(
                    """
                    SELECT rca_status, COUNT(*) as count
                    FROM baselinr_rca_results
                    GROUP BY rca_status
                """
                )
                result = conn.execute(count_query)

                for row in result:
                    status = row[0]
                    count = row[1]

                    if status == "analyzed":
                        stats["analyzed"] = count
                    elif status == "dismissed":
                        stats["dismissed"] = count
                    elif status == "pending":
                        stats["pending"] = count

                stats["total_analyses"] = stats["analyzed"] + stats["dismissed"] + stats["pending"]

                # Calculate average causes
                avg_query = text(
                    """
                    SELECT AVG(JSON_LENGTH(probable_causes))
                    FROM baselinr_rca_results
                    WHERE rca_status = 'analyzed'
                """
                )

                try:
                    result = conn.execute(avg_query)
                    avg_row: Any = result.fetchone()  # type: ignore[assignment]
                    if avg_row is not None and len(avg_row) > 0 and avg_row[0] is not None:
                        stats["avg_causes_per_anomaly"] = float(avg_row[0])
                except Exception:
                    # JSON_LENGTH may not be available
                    pass

        except Exception as e:
            logger.error(f"Error getting RCA statistics: {e}")

        return stats

    def get_recent_rca_results(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent RCA results.

        Args:
            limit: Maximum number of results

        Returns:
            List of RCA result dictionaries
        """
        from sqlalchemy import text

        query = text(
            f"""
            SELECT anomaly_id, table_name, schema_name, column_name, metric_name,
                   analyzed_at, rca_status, probable_causes, impact_analysis
            FROM baselinr_rca_results
            ORDER BY analyzed_at DESC
            LIMIT {limit}
        """
        )

        results = []

        try:
            import json

            with self.engine.connect() as conn:
                result = conn.execute(query)
                rows = result.fetchall()

                for row in rows:
                    probable_causes = json.loads(row[7]) if row[7] else []
                    impact_analysis = json.loads(row[8]) if row[8] else None

                    results.append(
                        {
                            "anomaly_id": row[0],
                            "table_name": row[1],
                            "schema_name": row[2],
                            "column_name": row[3],
                            "metric_name": row[4],
                            "analyzed_at": row[5].isoformat() if row[5] else None,
                            "rca_status": row[6],
                            "num_causes": len(probable_causes),
                            "top_cause": probable_causes[0] if probable_causes else None,
                            "impact_analysis": impact_analysis,
                        }
                    )

        except Exception as e:
            logger.error(f"Error getting recent RCA results: {e}")

        return results
