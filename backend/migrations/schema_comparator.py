"""
Schema Comparator - Compares SQLAlchemy models against the live PostgreSQL schema.
"""
from sqlalchemy import inspect, MetaData, DateTime
from sqlalchemy.engine import Engine
from typing import List, Any
from dataclasses import dataclass
import re


@dataclass
class ColumnDifference:
    table_name: str
    column_name: str
    change_type: str  # 'add', 'modify', 'drop'
    model_type: Any = None
    db_type: Any = None


@dataclass
class TableDifference:
    table_name: str
    change_type: str  # 'add', 'drop'


@dataclass
class IndexDifference:
    table_name: str
    index_name: str
    change_type: str  # 'add', 'drop'
    columns: List[str] = None


@dataclass
class SchemaDiff:
    tables_to_add: List[TableDifference]
    tables_to_drop: List[TableDifference]
    columns_to_add: List[ColumnDifference]
    columns_to_modify: List[ColumnDifference]
    columns_to_drop: List[ColumnDifference]
    indexes_to_add: List[IndexDifference]
    indexes_to_drop: List[IndexDifference]

    def has_changes(self) -> bool:
        return bool(
            self.tables_to_add or self.columns_to_add or
            self.columns_to_modify or self.columns_to_drop or
            self.indexes_to_add
        )


class SchemaComparator:
    def __init__(self, engine: Engine, metadata: MetaData):
        self.engine = engine
        self.metadata = metadata
        self.inspector = inspect(engine)

    def _model_pg_type(self, col_type) -> str:
        """Convert a SQLAlchemy model type object to its canonical PostgreSQL type string.

        Uses the type object directly (not its string repr) so DateTime(timezone=True)
        maps to TIMESTAMPTZ rather than the generic DATETIME string.
        """
        name = type(col_type).__name__

        if name == 'UUID':
            return 'UUID'
        if name == 'Boolean':
            return 'BOOLEAN'
        if name == 'BigInteger':
            return 'BIGINT'
        if name in ('Integer', 'INT'):
            return 'INTEGER'
        if name in ('Float', 'Double', 'REAL'):
            return 'DOUBLE PRECISION'
        if name in ('Numeric', 'Decimal'):
            p, s = getattr(col_type, 'precision', None), getattr(col_type, 'scale', None)
            return f'NUMERIC({p}, {s})' if p and s else 'NUMERIC'
        if name == 'DateTime':
            return 'TIMESTAMPTZ' if getattr(col_type, 'timezone', False) else 'TIMESTAMP'
        if name == 'Text':
            return 'TEXT'
        if name == 'String':
            length = getattr(col_type, 'length', None)
            return f'VARCHAR({length})' if length else 'TEXT'

        return self._normalize_db_type(str(col_type))

    def _normalize_db_type(self, type_str: str) -> str:
        """Normalize a PostgreSQL-reported type string to a canonical form for comparison.

        PostgreSQL reports types in lowercase with verbose names:
          'character varying(255)' instead of VARCHAR(255)
          'timestamp with time zone' instead of TIMESTAMPTZ
          'double precision' instead of FLOAT
        """
        t = type_str.upper().strip()

        if t in ('BOOLEAN', 'BOOL'):
            return 'BOOLEAN'
        if t in ('UUID',):
            return 'UUID'
        if t in ('INTEGER', 'INT', 'INT4'):
            return 'INTEGER'
        if t in ('BIGINT', 'INT8'):
            return 'BIGINT'
        if t in ('DOUBLE PRECISION', 'FLOAT', 'FLOAT4', 'FLOAT8', 'REAL'):
            return 'DOUBLE PRECISION'
        if 'TIMESTAMPTZ' in t or 'WITH TIME ZONE' in t:
            return 'TIMESTAMPTZ'
        if 'TIMESTAMP' in t or 'DATETIME' in t:
            return 'TIMESTAMP'
        if 'CHARACTER VARYING' in t or 'VARCHAR' in t:
            m = re.search(r'\((\d+)\)', t)
            return f'VARCHAR({m.group(1)})' if m else 'TEXT'
        if t == 'TEXT':
            return 'TEXT'
        if 'NUMERIC' in t or 'DECIMAL' in t:
            m = re.search(r'\((\d+),\s*(\d+)\)', t)
            return f'NUMERIC({m.group(1)}, {m.group(2)})' if m else 'NUMERIC'

        return t

    def compare_schemas(self) -> SchemaDiff:
        """Compare SQLAlchemy metadata against the live database and return all differences."""
        db_tables = set(self.inspector.get_table_names())
        model_tables = set(self.metadata.tables.keys())

        tables_to_add, tables_to_drop = [], []
        columns_to_add, columns_to_modify, columns_to_drop = [], [], []
        indexes_to_add, indexes_to_drop = [], []

        for t in model_tables - db_tables:
            tables_to_add.append(TableDifference(table_name=t, change_type='add'))

        for t in db_tables - model_tables:
            tables_to_drop.append(TableDifference(table_name=t, change_type='drop'))

        for table_name in model_tables & db_tables:
            model_table = self.metadata.tables[table_name]
            db_cols = {c['name']: c for c in self.inspector.get_columns(table_name)}
            model_cols = {c.name: c for c in model_table.columns}

            for col_name in set(model_cols) - set(db_cols):
                columns_to_add.append(ColumnDifference(
                    table_name=table_name, column_name=col_name,
                    change_type='add', model_type=model_cols[col_name].type,
                ))

            for col_name in set(db_cols) - set(model_cols):
                columns_to_drop.append(ColumnDifference(
                    table_name=table_name, column_name=col_name,
                    change_type='drop', db_type=db_cols[col_name]['type'],
                ))

            for col_name in set(model_cols) & set(db_cols):
                model_col = model_cols[col_name]
                db_col = db_cols[col_name]

                model_type_str = self._model_pg_type(model_col.type)
                db_type_str = self._normalize_db_type(str(db_col['type']))

                if model_type_str != db_type_str or model_col.nullable != db_col['nullable']:
                    columns_to_modify.append(ColumnDifference(
                        table_name=table_name, column_name=col_name,
                        change_type='modify',
                        model_type=model_col.type,
                        db_type=db_col['type'],
                    ))

            db_indexes = {i['name']: i for i in self.inspector.get_indexes(table_name)}
            model_indexes = {i.name: i for i in model_table.indexes if i.name}

            for idx_name in set(model_indexes) - set(db_indexes):
                idx = model_indexes[idx_name]
                indexes_to_add.append(IndexDifference(
                    table_name=table_name, index_name=idx_name,
                    change_type='add', columns=[c.name for c in idx.columns],
                ))

        return SchemaDiff(
            tables_to_add=tables_to_add, tables_to_drop=tables_to_drop,
            columns_to_add=columns_to_add, columns_to_modify=columns_to_modify,
            columns_to_drop=columns_to_drop,
            indexes_to_add=indexes_to_add, indexes_to_drop=indexes_to_drop,
        )
