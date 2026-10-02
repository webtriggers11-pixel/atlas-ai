"""
Unit tests for the SQL our custom migration system generates — no database needed.
Run from backend/: pytest tests/test_migrator.py -v
"""
from sqlalchemy import MetaData, Table, Column, Integer, Text, ForeignKey, Index, Computed
from sqlalchemy.dialects.postgresql import UUID, TSVECTOR
from pgvector.sqlalchemy import Vector

from migrations.schema_comparator import SchemaDiff, TableDifference, IndexDifference, ColumnDifference, SchemaComparator
from migrations.sql_generator import SQLGenerator


def _empty_diff(**overrides) -> SchemaDiff:
    """Build a SchemaDiff with every list empty unless overridden."""
    fields = dict(tables_to_add=[], tables_to_drop=[], columns_to_add=[], columns_to_modify=[],
                  columns_to_drop=[], indexes_to_add=[], indexes_to_drop=[], extensions_to_add=[])
    fields.update(overrides)
    return SchemaDiff(**fields)


def _metadata() -> MetaData:
    """Two related tables: parent + child with an FK, a vector column and a generated tsvector."""
    md = MetaData()
    Table("parents", md, Column("id", UUID(as_uuid=True), primary_key=True))
    Table(
        "children", md,
        Column("id", UUID(as_uuid=True), primary_key=True),
        Column("parent_id", UUID(as_uuid=True), ForeignKey("parents.id", ondelete="CASCADE"), nullable=False),
        Column("content", Text, nullable=False),
        Column("embedding", Vector(384), nullable=True),
        Column("tsv", TSVECTOR, Computed("to_tsvector('english', content)", persisted=True)),
        Index("idx_children_embedding", "embedding", postgresql_using="hnsw",
              postgresql_ops={"embedding": "vector_cosine_ops"}),
        Index("uq_children_parent_content", "parent_id", "content", unique=True),
    )
    return md


def test_extension_is_created_first():
    """CREATE EXTENSION must come before any table that uses its types."""
    md = _metadata()
    diff = _empty_diff(extensions_to_add=["vector"], tables_to_add=[TableDifference("children", "add")])
    sql = SQLGenerator().generate_migration_sql(diff, md)
    assert sql[0] == "CREATE EXTENSION IF NOT EXISTS vector;"
    assert sql[1].startswith("CREATE TABLE children")


def test_create_table_has_inline_foreign_key_vector_and_generated_column():
    """CREATE TABLE includes REFERENCES ... ON DELETE CASCADE, VECTOR(384) and a STORED generated column."""
    md = _metadata()
    sql = SQLGenerator()._create_table("children", md)
    assert "parent_id UUID NOT NULL REFERENCES parents (id) ON DELETE CASCADE" in sql
    assert "embedding VECTOR(384)" in sql
    assert "tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED" in sql


def test_hnsw_and_unique_indexes():
    """Index options (USING hnsw + operator class, UNIQUE) are turned into the right DDL."""
    md = _metadata()
    table = md.tables["children"]
    indexes = {i.name: SchemaComparator._index_difference("children", i) for i in table.indexes}
    gen = SQLGenerator()
    assert gen._create_index(indexes["idx_children_embedding"]) == (
        "CREATE INDEX idx_children_embedding ON children USING hnsw (embedding vector_cosine_ops);"
    )
    assert gen._create_index(indexes["uq_children_parent_content"]) == (
        "CREATE UNIQUE INDEX uq_children_parent_content ON children (parent_id, content);"
    )


def test_column_drops_are_skipped_by_default():
    """A column missing from the models is NOT dropped unless explicitly allowed."""
    diff = _empty_diff(columns_to_drop=[ColumnDifference("children", "old_col", "drop")])
    assert SQLGenerator(allow_drops=False).generate_migration_sql(diff, _metadata()) == []
    assert SQLGenerator(allow_drops=True).generate_migration_sql(diff, _metadata()) == [
        "ALTER TABLE children DROP COLUMN old_col;"
    ]


def test_vector_type_normalization_matches_db_report():
    """The model type and the type Postgres reports compare equal, so no endless ALTERs are generated."""
    comparator = SchemaComparator.__new__(SchemaComparator)  # type helpers need no DB connection
    assert comparator._model_pg_type(Vector(384)) == "VECTOR(384)"
    assert comparator._normalize_db_type("vector(384)") == "VECTOR(384)"
    assert comparator._model_pg_type(Integer()) == comparator._normalize_db_type("integer")


def test_reflected_timestamptz_is_not_reported_as_changed():
    """Regression: reflected TIMESTAMP(timezone=True) must normalize to TIMESTAMPTZ like the model type."""
    from sqlalchemy import DateTime
    from sqlalchemy.dialects.postgresql import TIMESTAMP

    comparator = SchemaComparator.__new__(SchemaComparator)
    assert comparator._db_pg_type(TIMESTAMP(timezone=True)) == comparator._model_pg_type(DateTime(timezone=True))
    assert comparator._db_pg_type(TIMESTAMP(timezone=False)) == "TIMESTAMP"
