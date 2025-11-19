"""
Schema change detection for Baselinr.

Detects schema changes including new/dropped/renamed columns,
type changes, and partition changes.
"""

import hashlib
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


class SchemaRegistry:
    """Manages schema snapshots and hashes in the storage database."""

    def __init__(self, engine: Engine, registry_table: str = "baselinr_schema_registry"):
        """
        Initialize schema registry.

        Args:
            engine: SQLAlchemy engine for storage database
            registry_table: Name of the registry table
        """
        self.engine = engine
        self.registry_table = registry_table

    def calculate_column_hash(
        self, column_name: str, column_type: str, nullable: bool = True
    ) -> str:
        """
        Calculate hash for a column structure.

        Args:
            column_name: Name of the column
            column_type: Data type of the column
            nullable: Whether column is nullable

        Returns:
            SHA256 hash of column structure
        """
        # Normalize type string (remove whitespace, lowercase)
        normalized_type = str(column_type).strip().lower()
        hash_input = f"{column_name}:{normalized_type}:{nullable}"
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def register_schema(
        self,
        table_name: str,
        schema_name: Optional[str],
        columns: Dict[str, str],
        run_id: str,
        profiled_at: datetime,
        nullable_info: Optional[Dict[str, bool]] = None,
    ):
        """
        Register a schema snapshot for a table.

        Args:
            table_name: Name of the table
            schema_name: Schema name (if applicable)
            columns: Dict mapping column_name -> column_type
            run_id: Run ID for this profiling run
            profiled_at: Timestamp of profiling
            nullable_info: Optional dict mapping column_name -> nullable boolean
        """
        if nullable_info is None:
            nullable_info = {}

        with self.engine.connect() as conn:
            for column_name, column_type in columns.items():
                nullable = nullable_info.get(column_name, True)
                column_hash = self.calculate_column_hash(column_name, column_type, nullable)

                # Check if column already exists in registry
                check_query = text(
                    f"""
                    SELECT id, first_seen_at FROM {self.registry_table}
                    WHERE table_name = :table_name
                    AND schema_name {'= :schema_name' if schema_name else 'IS NULL'}
                    AND column_name = :column_name
                    ORDER BY last_seen_at DESC
                    LIMIT 1
                """
                )

                params = {
                    "table_name": table_name,
                    "column_name": column_name,
                }
                if schema_name:
                    params["schema_name"] = schema_name

                existing = conn.execute(check_query, params).fetchone()

                if existing:
                    # Update existing record
                    update_query = text(
                        f"""
                        UPDATE {self.registry_table}
                        SET column_type = :column_type,
                            column_hash = :column_hash,
                            nullable = :nullable,
                            last_seen_at = :last_seen_at,
                            run_id = :run_id
                        WHERE id = :id
                    """
                    )
                    conn.execute(
                        update_query,
                        {
                            "id": existing[0],
                            "column_type": column_type,
                            "column_hash": column_hash,
                            "nullable": nullable,
                            "last_seen_at": profiled_at,
                            "run_id": run_id,
                        },
                    )
                else:
                    # Insert new record
                    insert_query = text(
                        f"""
                        INSERT INTO {self.registry_table}
                        (table_name, schema_name, column_name, column_type, column_hash,
                         nullable, first_seen_at, last_seen_at, run_id)
                        VALUES (:table_name, :schema_name, :column_name, :column_type, :column_hash,
                                :nullable, :first_seen_at, :last_seen_at, :run_id)
                    """
                    )
                    conn.execute(
                        insert_query,
                        {
                            "table_name": table_name,
                            "schema_name": schema_name,
                            "column_name": column_name,
                            "column_type": column_type,
                            "column_hash": column_hash,
                            "nullable": nullable,
                            "first_seen_at": profiled_at,
                            "last_seen_at": profiled_at,
                            "run_id": run_id,
                        },
                    )

            conn.commit()

    def get_previous_schema(
        self, table_name: str, schema_name: Optional[str], before_run_id: Optional[str] = None
    ) -> Dict[str, Tuple[str, str]]:
        """
        Get previous schema snapshot for a table.

        Args:
            table_name: Name of the table
            schema_name: Schema name (if applicable)
            before_run_id: Optional run_id to get schema before this run

        Returns:
            Dict mapping column_name -> (column_type, column_hash)
        """
        with self.engine.connect() as conn:
            if before_run_id:
                # Get schema from specific run
                query = text(
                    f"""
                    SELECT column_name, column_type, column_hash
                    FROM {self.registry_table}
                    WHERE table_name = :table_name
                    AND schema_name {'= :schema_name' if schema_name else 'IS NULL'}
                    AND run_id = :run_id
                """
                )
                params = {"table_name": table_name, "run_id": before_run_id}
                if schema_name:
                    params["schema_name"] = schema_name
            else:
                # Get most recent schema
                query = text(
                    f"""
                    SELECT column_name, column_type, column_hash
                    FROM {self.registry_table}
                    WHERE table_name = :table_name
                    AND schema_name {'= :schema_name' if schema_name else 'IS NULL'}
                    AND (table_name, schema_name, column_name, last_seen_at) IN (
                        SELECT table_name, schema_name, column_name, MAX(last_seen_at)
                        FROM {self.registry_table}
                        WHERE table_name = :table_name
                        AND schema_name {'= :schema_name' if schema_name else 'IS NULL'}
                        GROUP BY table_name, schema_name, column_name
                    )
                """
                )
                params = {"table_name": table_name}
                if schema_name:
                    params["schema_name"] = schema_name

            result = conn.execute(query, params).fetchall()
            return {row[0]: (row[1], row[2]) for row in result}


class ColumnRenamer:
    """Heuristic detection of renamed columns."""

    def __init__(self, similarity_threshold: float = 0.7):
        """
        Initialize column renamer.

        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) to consider a rename
        """
        self.similarity_threshold = similarity_threshold

    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two column names.

        Uses Levenshtein distance and common prefix/suffix matching.

        Args:
            name1: First column name
            name2: Second column name

        Returns:
            Similarity score between 0.0 and 1.0
        """
        name1_lower = name1.lower()
        name2_lower = name2.lower()

        # Exact match
        if name1_lower == name2_lower:
            return 1.0

        # Common prefix/suffix bonus
        prefix_match = 0
        suffix_match = 0
        min_len = min(len(name1_lower), len(name2_lower))

        for i in range(min_len):
            if name1_lower[i] == name2_lower[i]:
                prefix_match += 1
            else:
                break

        for i in range(1, min_len + 1):
            if name1_lower[-i] == name2_lower[-i]:
                suffix_match += 1
            else:
                break

        # Levenshtein distance
        distance = self._levenshtein_distance(name1_lower, name2_lower)
        max_len = max(len(name1_lower), len(name2_lower))
        levenshtein_similarity = 1.0 - (distance / max_len) if max_len > 0 else 0.0

        # Combine with prefix/suffix bonus
        prefix_bonus = (prefix_match / max_len) * 0.2 if max_len > 0 else 0
        suffix_bonus = (suffix_match / max_len) * 0.2 if max_len > 0 else 0

        similarity = levenshtein_similarity + prefix_bonus + suffix_bonus
        return min(1.0, similarity)

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row: List[int] = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def detect_renames(
        self,
        removed_columns: Set[str],
        added_columns: Set[str],
        removed_types: Dict[str, str],
        added_types: Dict[str, str],
    ) -> List[Tuple[str, str]]:
        """
        Detect likely column renames.

        Args:
            removed_columns: Set of removed column names
            added_columns: Set of added column names
            removed_types: Dict mapping removed column names to their types
            added_types: Dict mapping added column names to their types

        Returns:
            List of (old_name, new_name) tuples for likely renames
        """
        renames = []

        for old_name in removed_columns:
            old_type = removed_types.get(old_name, "")
            best_match = None
            best_similarity = 0.0

            for new_name in added_columns:
                new_type = added_types.get(new_name, "")
                # Check type compatibility
                if not self._types_compatible(old_type, new_type):
                    continue

                similarity = self.calculate_similarity(old_name, new_name)
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = new_name

            if best_match:
                renames.append((old_name, best_match))
                added_columns.remove(best_match)  # Remove from added to avoid duplicate matches

        return renames

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """
        Check if two types are compatible (likely same column).

        Args:
            type1: First type
            type2: Second type

        Returns:
            True if types are compatible
        """
        # Normalize types
        t1 = str(type1).lower().strip()
        t2 = str(type2).lower().strip()

        # Exact match
        if t1 == t2:
            return True

        # Compatible numeric types
        numeric_types = {
            "int",
            "integer",
            "bigint",
            "smallint",
            "tinyint",
            "float",
            "double",
            "decimal",
            "numeric",
        }
        if t1 in numeric_types and t2 in numeric_types:
            return True

        # Compatible string types
        string_types = {"varchar", "char", "text", "string", "nvarchar"}
        if t1 in string_types and t2 in string_types:
            return True

        # Compatible date types
        date_types = {"date", "timestamp", "datetime", "time"}
        if t1 in date_types and t2 in date_types:
            return True

        return False


class SchemaChangeDetector:
    """Detects schema changes between runs."""

    def __init__(
        self,
        registry: SchemaRegistry,
        renamer: Optional[ColumnRenamer] = None,
        similarity_threshold: float = 0.7,
    ):
        """
        Initialize schema change detector.

        Args:
            registry: SchemaRegistry instance
            renamer: Optional ColumnRenamer instance
            similarity_threshold: Similarity threshold for rename detection
        """
        self.registry = registry
        self.renamer = renamer or ColumnRenamer(similarity_threshold=similarity_threshold)

    def detect_changes(
        self,
        table_name: str,
        schema_name: Optional[str],
        current_columns: Dict[str, str],
        current_run_id: str,
        previous_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Detect schema changes between current and previous schema.

        Args:
            table_name: Name of the table
            schema_name: Schema name (if applicable)
            current_columns: Dict mapping column_name -> column_type for current schema
            current_run_id: Current run ID
            previous_run_id: Optional previous run ID to compare against

        Returns:
            Dict with detected changes:
            - added_columns: List of (column_name, column_type)
            - removed_columns: List of (column_name, column_type)
            - renamed_columns: List of (old_name, new_name, old_type, new_type)
            - type_changes: List of (column_name, old_type, new_type)
            - partition_changes: List of partition change info (if any)
        """
        # Get previous schema
        previous_schema = self.registry.get_previous_schema(
            table_name, schema_name, before_run_id=previous_run_id
        )

        previous_columns = {name: type_info[0] for name, type_info in previous_schema.items()}

        # Detect basic changes
        current_set = set(current_columns.keys())
        previous_set = set(previous_columns.keys())

        added_columns = current_set - previous_set
        removed_columns = previous_set - current_set
        common_columns = current_set & previous_set

        # Detect type changes
        type_changes = []
        for col in common_columns:
            old_type = previous_columns[col]
            new_type = current_columns[col]
            if old_type != new_type:
                type_changes.append((col, old_type, new_type))

        # Detect renames
        renamed_columns = []
        if added_columns and removed_columns:
            removed_types = {col: previous_columns[col] for col in removed_columns}
            added_types = {col: current_columns[col] for col in added_columns}
            renames = self.renamer.detect_renames(
                removed_columns, added_columns, removed_types, added_types
            )

            for old_name, new_name in renames:
                renamed_columns.append(
                    (old_name, new_name, previous_columns[old_name], current_columns[new_name])
                )
                # Remove from added/removed since they're renames
                added_columns.discard(new_name)
                removed_columns.discard(old_name)

        # Partition changes (placeholder - will be implemented separately)
        partition_changes: List[Dict[str, Any]] = []

        return {
            "added_columns": [(col, current_columns[col]) for col in added_columns],
            "removed_columns": [(col, previous_columns[col]) for col in removed_columns],
            "renamed_columns": renamed_columns,
            "type_changes": type_changes,
            "partition_changes": partition_changes,
        }

    def detect_partition_changes(
        self,
        table_name: str,
        schema_name: Optional[str],
        warehouse_type: str,
        connector: Any,
    ) -> List[Dict[str, Any]]:
        """
        Detect partition changes (warehouse-specific).

        Args:
            table_name: Name of the table
            schema_name: Schema name (if applicable)
            warehouse_type: Type of warehouse (snowflake, etc.)
            connector: Database connector instance

        Returns:
            List of partition change dictionaries
        """
        changes = []

        if warehouse_type == "snowflake":
            try:
                # Query Snowflake partition metadata
                # Note: This requires appropriate permissions
                query = f"""
                    SELECT
                        CLUSTERING_KEY,
                        ROW_COUNT,
                        BYTES
                    FROM INFORMATION_SCHEMA.TABLE_STORAGE_METRICS
                    WHERE TABLE_SCHEMA = UPPER('{schema_name or "PUBLIC"}')
                    AND TABLE_NAME = UPPER('{table_name}')
                """
                try:
                    results = connector.execute_query(query)
                    if results:
                        changes.append(
                            {
                                "clustering_key": results[0].get("CLUSTERING_KEY"),
                                "row_count": results[0].get("ROW_COUNT"),
                                "bytes": results[0].get("BYTES"),
                            }
                        )
                except Exception as query_error:
                    logger.debug(
                        f"Could not query Snowflake partition metadata "
                        f"(may require permissions): {query_error}"
                    )
            except Exception as e:
                logger.warning(f"Failed to detect partition changes: {e}")

        # For other warehouses, partition detection would need to be implemented
        # based on their specific metadata tables/views

        return changes
