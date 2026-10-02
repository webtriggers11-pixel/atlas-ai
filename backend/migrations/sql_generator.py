"""
SQL Generator - Generates PostgreSQL DDL from schema diffs.
"""
import enum
import os
from typing import List
from sqlalchemy import DateTime, Text, String, Boolean, Integer, BigInteger, Float, Numeric
from migrations.schema_comparator import (
    SchemaDiff, ColumnDifference, TableDifference, IndexDifference
)

# Import UUID type safely — it lives in the PostgreSQL dialect
try:
    from sqlalchemy.dialects.postgresql import UUID as PG_UUID
except ImportError:
    PG_UUID = None


class SQLGenerator:
    """Generates PostgreSQL-compatible DDL statements from a SchemaDiff."""

    def __init__(self, allow_drops: bool | None = None):
        """allow_drops=None reads MIGRATIONS_ALLOW_DROPS from the environment (default: false)."""
        if allow_drops is None:
            allow_drops = os.getenv("MIGRATIONS_ALLOW_DROPS", "false").lower() == "true"
        self.allow_drops = allow_drops

    # PostgreSQL reserved words that need double-quote quoting as identifiers
    PG_RESERVED = {
        'all', 'analyse', 'analyze', 'and', 'any', 'array', 'as', 'asc',
        'asymmetric', 'both', 'case', 'cast', 'check', 'collate', 'column',
        'constraint', 'create', 'cross', 'current_catalog', 'current_date',
        'current_role', 'current_schema', 'current_time', 'current_timestamp',
        'current_user', 'default', 'deferrable', 'desc', 'distinct', 'do',
        'else', 'end', 'except', 'false', 'fetch', 'for', 'foreign', 'from',
        'full', 'grant', 'group', 'having', 'in', 'initially', 'inner',
        'intersect', 'into', 'lateral', 'leading', 'left', 'like', 'limit',
        'localtime', 'localtimestamp', 'natural', 'not', 'null', 'offset',
        'on', 'only', 'open', 'or', 'order', 'outer', 'overlaps', 'placing',
        'primary', 'references', 'returning', 'right', 'select', 'session_user',
        'similar', 'some', 'symmetric', 'table', 'then', 'to', 'trailing',
        'true', 'union', 'unique', 'user', 'using', 'variadic', 'verbose',
        'when', 'where', 'window', 'with',
    }

    def _q(self, name: str) -> str:
        """Double-quote an identifier only when it collides with a PostgreSQL reserved word."""
        return f'"{name}"' if name.lower() in self.PG_RESERVED else name

    def _pg_type(self, col_type) -> str:
        """Map a SQLAlchemy column type object to its PostgreSQL DDL type string."""
        if PG_UUID and isinstance(col_type, PG_UUID):
            return 'UUID'
        if isinstance(col_type, Boolean):
            return 'BOOLEAN'
        if isinstance(col_type, BigInteger):
            return 'BIGINT'
        if isinstance(col_type, Integer):
            return 'INTEGER'
        if isinstance(col_type, Float):
            return 'DOUBLE PRECISION'
        if isinstance(col_type, Numeric):
            p, s = col_type.precision, col_type.scale
            return f'NUMERIC({p}, {s})' if p and s else 'NUMERIC'
        if isinstance(col_type, DateTime):
            return 'TIMESTAMPTZ' if col_type.timezone else 'TIMESTAMP'
        if isinstance(col_type, Text):
            return 'TEXT'
        if isinstance(col_type, String):
            return f'VARCHAR({col_type.length})' if col_type.length else 'TEXT'
        if type(col_type).__name__ == 'Vector':
            return f'VECTOR({col_type.dim})'
        # Fallback for any type not handled above
        return str(col_type).upper()

    def _col_def(self, col, in_create: bool) -> str:
        """Build the full column definition string for CREATE TABLE or ADD COLUMN."""
        parts = [self._q(col.name), self._pg_type(col.type)]

        # Generated column, e.g. tsvector computed from another column — no NOT NULL / DEFAULT allowed
        if col.computed is not None:
            parts.append(f"GENERATED ALWAYS AS ({col.computed.sqltext}) STORED")
            return " ".join(parts)

        if not col.nullable:
            parts.append("NOT NULL")

        # server_default writes the DEFAULT clause directly into DDL
        if col.server_default is not None:
            parts.append(f"DEFAULT {col.server_default.arg}")
        elif col.default is not None and hasattr(col.default, 'arg'):
            arg = col.default.arg
            if not callable(arg):
                if isinstance(arg, enum.Enum):
                    arg = arg.value
                if isinstance(arg, bool):
                    parts.append(f"DEFAULT {'true' if arg else 'false'}")
                elif isinstance(arg, str):
                    parts.append(f"DEFAULT '{arg}'")
                else:
                    parts.append(f"DEFAULT {arg}")

        parts.extend(self._fk_clause(fk) for fk in col.foreign_keys)
        return " ".join(parts)

    def _fk_clause(self, fk) -> str:
        """Build an inline 'REFERENCES table(col) ON DELETE ...' clause for a column's ForeignKey."""
        target = fk.column
        clause = f"REFERENCES {target.table.name} ({self._q(target.name)})"
        if fk.ondelete:
            clause += f" ON DELETE {fk.ondelete.upper()}"
        return clause

    def _create_index(self, i: IndexDifference) -> str:
        """Build CREATE [UNIQUE] INDEX, honouring USING (hnsw/gin) and per-column operator classes."""
        unique = "UNIQUE " if i.unique else ""
        using = f" USING {i.using}" if i.using else ""
        ops = i.ops or {}
        cols = ", ".join(
            f"{self._q(c)} {ops[c]}" if c in ops else self._q(c) for c in i.columns
        )
        return f"CREATE {unique}INDEX {i.index_name} ON {i.table_name}{using} ({cols});"

    def generate_migration_sql(self, diff: SchemaDiff, metadata) -> List[str]:
        """Generate DDL in safe order: EXTENSION → CREATE TABLE → ADD COLUMN → MODIFY → DROP → INDEX."""
        stmts = [f"CREATE EXTENSION IF NOT EXISTS {ext};" for ext in diff.extensions_to_add]
        new_cols: set[tuple[str, str]] = set()

        for t in diff.tables_to_add:
            s = self._create_table(t.table_name, metadata)
            if s:
                stmts.append(s)

        for c in diff.columns_to_add:
            s = self._add_column(c, metadata)
            if s:
                stmts.append(s)
                new_cols.add((c.table_name, c.column_name))

        for c in diff.columns_to_modify:
            s = self._modify_column(c, metadata)
            if s:
                stmts.append(s)

        for c in diff.columns_to_drop:
            if self.allow_drops:
                stmts.append(f"ALTER TABLE {c.table_name} DROP COLUMN {self._q(c.column_name)};")
            else:
                # Destructive DDL is never generated by default: a renamed model field would
                # otherwise silently delete the old column's data. Drop by hand after review.
                print(f"  [SKIP] {c.table_name}.{c.column_name} exists in DB but not in models — "
                      f"not dropped (set MIGRATIONS_ALLOW_DROPS=true to allow).")

        add_col_keys = {(c.table_name, c.column_name) for c in diff.columns_to_add}
        for i in diff.indexes_to_add:
            missing = [c for c in i.columns if (i.table_name, c) in add_col_keys and (i.table_name, c) not in new_cols]
            if missing:
                print(f"  [WARN] Skipping index {i.index_name}: columns {missing} not yet added.")
                continue
            stmts.append(self._create_index(i))

        return stmts

    def _create_table(self, table_name: str, metadata) -> str:
        """Generate a full CREATE TABLE statement including PK and unique constraints."""
        if table_name not in metadata.tables:
            return None

        table = metadata.tables[table_name]
        parts = [self._col_def(col, in_create=True) for col in table.columns]

        pk_cols = [self._q(c.name) for c in table.columns if c.primary_key]
        if pk_cols:
            parts.append(f"PRIMARY KEY ({', '.join(pk_cols)})")

        for constraint in table.constraints:
            if constraint.__class__.__name__ == 'UniqueConstraint':
                cols = [self._q(c.name) for c in constraint.columns]
                name = constraint.name or f"uq_{'_'.join(cols)}"
                parts.append(f"CONSTRAINT {name} UNIQUE ({', '.join(cols)})")
            if constraint.__class__.__name__ == 'CheckConstraint':
                name = constraint.name or ''
                name_clause = f"CONSTRAINT {name} " if name else ''
                parts.append(f"{name_clause}CHECK ({constraint.sqltext})")

        return f"CREATE TABLE {table_name} (\n  " + ",\n  ".join(parts) + "\n);"

    def _add_column(self, col_diff: ColumnDifference, metadata) -> str:
        """Generate ALTER TABLE ... ADD COLUMN for a new column."""
        table = metadata.tables.get(col_diff.table_name)
        if table is None:
            return None
        col = table.columns.get(col_diff.column_name)
        if col is None:
            return None
        return f"ALTER TABLE {col_diff.table_name} ADD COLUMN {self._col_def(col, in_create=False)};"

    def _modify_column(self, col_diff: ColumnDifference, metadata) -> str:
        """Generate ALTER COLUMN TYPE + SET/DROP NOT NULL (PostgreSQL syntax)."""
        table = metadata.tables.get(col_diff.table_name)
        if table is None:
            return None
        col = table.columns.get(col_diff.column_name)
        if col is None:
            return None

        col_name = self._q(col.name)
        t = col_diff.table_name
        pg_type = self._pg_type(col.type)
        null_clause = "DROP NOT NULL" if col.nullable else "SET NOT NULL"

        return (
            f"ALTER TABLE {t} ALTER COLUMN {col_name} TYPE {pg_type};\n"
            f"ALTER TABLE {t} ALTER COLUMN {col_name} {null_clause};"
        )
