"""
Pydantic models for table discovery API requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ColumnInfo(BaseModel):
    """Column metadata information."""
    name: str = Field(..., description="Column name")
    type: str = Field(..., description="Column data type")
    nullable: bool = Field(..., description="Whether column is nullable")


class TableInfo(BaseModel):
    """Individual table information."""
    schema: str = Field(..., description="Schema name")
    table: str = Field(..., description="Table name")
    table_type: Optional[str] = Field(None, description="Table type: table, view, materialized_view")
    row_count: Optional[int] = Field(None, description="Row count (if available)")
    database: Optional[str] = Field(None, description="Database name")
    tags: Optional[List[str]] = Field(default_factory=list, description="Table tags")


class TableDiscoveryResponse(BaseModel):
    """Response model for GET /api/tables/discover."""
    tables: List[TableInfo] = Field(default_factory=list, description="List of discovered tables")
    total: int = Field(..., description="Total number of tables found")
    schemas: List[str] = Field(default_factory=list, description="List of schemas discovered")


class TablePatternRequest(BaseModel):
    """Request body for POST /api/tables/discover."""
    database: Optional[str] = Field(None, description="Database name")
    schema: Optional[str] = Field(None, description="Schema name")
    table: Optional[str] = Field(None, description="Explicit table name")
    pattern: Optional[str] = Field(None, description="Wildcard or regex pattern")
    pattern_type: Optional[str] = Field(None, description="Pattern type: 'wildcard' or 'regex'")
    schema_pattern: Optional[str] = Field(None, description="Schema pattern")
    select_all_schemas: Optional[bool] = Field(None, description="Select all schemas")
    select_schema: Optional[bool] = Field(None, description="Select all tables in schema")
    tags: Optional[List[str]] = Field(None, description="Required tags (AND logic)")
    tags_any: Optional[List[str]] = Field(None, description="Optional tags (OR logic)")
    dbt_ref: Optional[str] = Field(None, description="dbt model reference")
    dbt_selector: Optional[str] = Field(None, description="dbt selector")
    exclude_patterns: Optional[List[str]] = Field(None, description="Exclude patterns")


class TablePreviewResponse(BaseModel):
    """Response model for POST /api/tables/discover."""
    tables: List[TableInfo] = Field(default_factory=list, description="List of matching tables")
    total: int = Field(..., description="Total number of matching tables")
    pattern: str = Field(..., description="Pattern that was matched")


class TableMetadataResponse(BaseModel):
    """Response model for GET /api/tables/{schema}/{table}/preview."""
    schema: str = Field(..., description="Schema name")
    table: str = Field(..., description="Table name")
    columns: List[ColumnInfo] = Field(default_factory=list, description="List of columns")
    row_count: Optional[int] = Field(None, description="Row count (if available)")
    table_type: Optional[str] = Field(None, description="Table type: table, view, materialized_view")

