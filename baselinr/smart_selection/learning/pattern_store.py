"""
Pattern store for persisting learned patterns.

Provides storage and retrieval of learned column patterns
for improved recommendations over time.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml  # type: ignore[import-untyped]

from .pattern_learner import LearnedPattern

logger = logging.getLogger(__name__)


class PatternStore:
    """
    Persistent storage for learned column patterns.

    Stores patterns in a YAML or JSON file for retrieval
    across sessions.
    """

    DEFAULT_FILENAME = ".baselinr_patterns.yaml"

    def __init__(
        self,
        storage_path: Optional[str] = None,
        auto_save: bool = True,
    ):
        """
        Initialize pattern store.

        Args:
            storage_path: Path to pattern storage file
            auto_save: Whether to auto-save after modifications
        """
        self.storage_path = storage_path or self._get_default_path()
        self.auto_save = auto_save
        self._patterns: Dict[str, LearnedPattern] = {}
        self._metadata: Dict[str, Any] = {
            "version": 1,
            "created_at": None,
            "updated_at": None,
            "pattern_count": 0,
        }

        # Load existing patterns if available
        self._load()

    def _get_default_path(self) -> str:
        """Get default storage path."""
        # Try current directory first, then user home
        cwd_path = Path.cwd() / self.DEFAULT_FILENAME
        if cwd_path.parent.exists():
            return str(cwd_path)

        home_path = Path.home() / ".baselinr" / "learned_patterns.yaml"
        home_path.parent.mkdir(parents=True, exist_ok=True)
        return str(home_path)

    def add_patterns(self, patterns: List[LearnedPattern]) -> int:
        """
        Add or update patterns.

        Args:
            patterns: List of patterns to add

        Returns:
            Number of patterns added or updated
        """
        added = 0

        for pattern in patterns:
            key = self._pattern_key(pattern)

            if key in self._patterns:
                # Update existing pattern
                existing = self._patterns[key]
                # Increase confidence if seen again
                existing.confidence = min(
                    0.99,
                    existing.confidence + (pattern.confidence * 0.1),
                )
                existing.occurrence_count += pattern.occurrence_count
                existing.source_columns.extend(pattern.source_columns)
                # Keep unique sources
                existing.source_columns = list(set(existing.source_columns))
            else:
                self._patterns[key] = pattern
                added += 1

        self._metadata["updated_at"] = datetime.utcnow().isoformat()
        self._metadata["pattern_count"] = len(self._patterns)

        if self.auto_save:
            self.save()

        return added

    def get_patterns(
        self,
        pattern_type: Optional[str] = None,
        min_confidence: float = 0.0,
    ) -> List[LearnedPattern]:
        """
        Get stored patterns.

        Args:
            pattern_type: Optional filter by pattern type
            min_confidence: Minimum confidence threshold

        Returns:
            List of matching patterns
        """
        patterns = list(self._patterns.values())

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        if min_confidence > 0:
            patterns = [p for p in patterns if p.confidence >= min_confidence]

        # Sort by confidence
        patterns.sort(key=lambda p: p.confidence, reverse=True)

        return patterns

    def get_pattern(self, pattern: str) -> Optional[LearnedPattern]:
        """
        Get a specific pattern.

        Args:
            pattern: Pattern string to look up

        Returns:
            LearnedPattern or None
        """
        for key, p in self._patterns.items():
            if p.pattern == pattern:
                return p
        return None

    def remove_pattern(self, pattern: str) -> bool:
        """
        Remove a pattern.

        Args:
            pattern: Pattern string to remove

        Returns:
            True if removed, False if not found
        """
        for key, p in list(self._patterns.items()):
            if p.pattern == pattern:
                del self._patterns[key]
                self._metadata["pattern_count"] = len(self._patterns)
                if self.auto_save:
                    self.save()
                return True
        return False

    def clear(self) -> None:
        """Clear all patterns."""
        self._patterns.clear()
        self._metadata["pattern_count"] = 0
        self._metadata["updated_at"] = datetime.utcnow().isoformat()

        if self.auto_save:
            self.save()

    def save(self) -> bool:
        """
        Save patterns to storage file.

        Returns:
            True if saved successfully
        """
        try:
            data = {
                "metadata": self._metadata,
                "learned_patterns": [p.to_dict() for p in self._patterns.values()],
            }

            # Ensure directory exists
            Path(self.storage_path).parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, "w") as f:
                if self.storage_path.endswith(".json"):
                    json.dump(data, f, indent=2, default=str)
                else:
                    yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            logger.debug(f"Saved {len(self._patterns)} patterns to {self.storage_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
            return False

    def _load(self) -> bool:
        """
        Load patterns from storage file.

        Returns:
            True if loaded successfully
        """
        if not os.path.exists(self.storage_path):
            return False

        try:
            with open(self.storage_path, "r") as f:
                if self.storage_path.endswith(".json"):
                    data = json.load(f)
                else:
                    data = yaml.safe_load(f)

            if not data:
                return False

            # Load metadata
            self._metadata.update(data.get("metadata", {}))

            # Load patterns
            for pattern_data in data.get("learned_patterns", []):
                pattern = self._dict_to_pattern(pattern_data)
                if pattern:
                    key = self._pattern_key(pattern)
                    self._patterns[key] = pattern

            logger.debug(f"Loaded {len(self._patterns)} patterns from {self.storage_path}")
            return True

        except Exception as e:
            logger.warning(f"Failed to load patterns from {self.storage_path}: {e}")
            return False

    def _pattern_key(self, pattern: LearnedPattern) -> str:
        """Generate a unique key for a pattern."""
        return f"{pattern.pattern_type}:{pattern.pattern}"

    def _dict_to_pattern(self, data: Dict[str, Any]) -> Optional[LearnedPattern]:
        """Convert a dictionary to a LearnedPattern."""
        try:
            checks = []
            for check in data.get("checks", []):
                if isinstance(check, dict):
                    checks.append(check.get("type", ""))
                elif isinstance(check, str):
                    checks.append(check)

            return LearnedPattern(
                pattern=data.get("pattern", ""),
                pattern_type=data.get("pattern_type", "unknown"),
                suggested_checks=[c for c in checks if c],
                confidence=float(data.get("confidence", 0.5)),
                occurrence_count=int(data.get("occurrence_count", 1)),
                metadata=data.get("metadata", {}),
            )
        except Exception as e:
            logger.debug(f"Failed to parse pattern: {e}")
            return None

    def get_metadata(self) -> Dict[str, Any]:
        """Get store metadata."""
        return self._metadata.copy()

    def export_to_config(self) -> Dict[str, Any]:
        """
        Export patterns in config file format.

        Returns:
            Dictionary suitable for config file 'patterns' section
        """
        return {"patterns": [p.to_config_format() for p in self._patterns.values()]}

    def import_from_config(self, config: Dict[str, Any]) -> int:
        """
        Import patterns from config file format.

        Args:
            config: Configuration with 'patterns' section

        Returns:
            Number of patterns imported
        """
        patterns_config = config.get("patterns", [])
        imported = 0

        for pattern_cfg in patterns_config:
            if not isinstance(pattern_cfg, dict):
                continue

            match = pattern_cfg.get("match", "")
            if not match:
                continue

            # Determine pattern type
            if match.endswith("*"):
                pattern_type = "prefix"
            elif match.startswith("*"):
                pattern_type = "suffix"
            else:
                pattern_type = "exact"

            # Extract checks
            checks = []
            for check in pattern_cfg.get("checks", []):
                if isinstance(check, dict):
                    checks.append(check.get("type", ""))
                elif isinstance(check, str):
                    checks.append(check)

            if checks:
                pattern = LearnedPattern(
                    pattern=match,
                    pattern_type=pattern_type,
                    suggested_checks=[c for c in checks if c],
                    confidence=float(pattern_cfg.get("confidence", 0.9)),
                )
                key = self._pattern_key(pattern)
                self._patterns[key] = pattern
                imported += 1

        if imported > 0:
            self._metadata["updated_at"] = datetime.utcnow().isoformat()
            self._metadata["pattern_count"] = len(self._patterns)
            if self.auto_save:
                self.save()

        return imported
