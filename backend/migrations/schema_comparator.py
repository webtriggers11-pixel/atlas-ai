"""
Schema Comparator - Compares SQLAlchemy models against the live PostgreSQL schema.
"""
from sqlalchemy import inspect, MetaData, DateTime
from sqlalchemy.engine import Engine
from typing import List, Any
from dataclasses import dataclass, field
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
    unique: bool = False
    using: str = None          # access method, e.g. 'hnsw' or 'gin' (None = btree)
    ops: dict = None           # per-column operator class, e.g. {'embedding': 'vector_cosine_ops'}


@dataclass
class SchemaDiff:
    tables_to_add: List[TableDifference]
    tables_to_drop: List[TableDifference]
    columns_to_add: List[ColumnDifference]
    columns_to_modify: List[ColumnDifference]
    columns_to_drop: List[ColumnDifference]
    indexes_to_add: List[IndexDifference]
    indexes_to_drop: List[IndexDifference]
    extensions_to_add: List[str] = field(default_factory=list)

    def has_changes(self) -> bool:
        """True when there is anything to apply (table drops are never applied automatically)."""
        return bool(
            self.extensions_to_add or
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
        if name == 'Vector':
            return f'VECTOR({col_type.dim})'
        if name == 'TSVECTOR':
            return 'TSVECTOR'

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
        if t.startswith('VECTOR'):
            m = re.search(r'\((\d+)\)', t)
            return f'VECTOR({m.group(1)})' if m else 'VECTOR'

        return t

    def _db_pg_type(self, db_type) -> str:
        """Canonical type string for a column type reflected from the database.

        Reflection returns TIMESTAMP(timezone=True) whose str() is just 'TIMESTAMP',
        so the timezone flag must be read from the object — otherwise every TIMESTAMPTZ
        column looks changed and a pointless ALTER is generated on every run.
        """
        if type(db_type).__name__ in ("TIMESTAMP", "DateTime"):
            return 'TIMESTAMPTZ' if getattr(db_type, 'timezone', False) else 'TIMESTAMP'
        return self._normalize_db_type(str(db_type))

    def _installed_extensions(self) -> set:
        """Return the names of extensions already installed in the connected database."""
        from sqlalchemy import text
        with self.engine.connect() as conn:
            return {row[0] for row in conn.execute(text("SELECT extname FROM pg_extension"))}

    def compare_schemas(self) -> SchemaDiff:
        """Compare SQLAlchemy metadata against the live database and return all differences."""
        db_tables = set(self.inspector.get_table_names())
        model_tables = set(self.metadata.tables.keys())

        tables_to_add, tables_to_drop = [], []
        columns_to_add, columns_to_modify, columns_to_drop = [], [], []
        indexes_to_add, indexes_to_drop = [], []

        # Create new tables parent-first so inline FOREIGN KEY references always resolve
        for table in self.metadata.sorted_tables:
            if table.name not in db_tables:
                tables_to_add.append(TableDifference(table_name=table.name, change_type='add'))
                # indexes of a brand-new table are created in the same migration, right after it
                indexes_to_add.extend(
                    self._index_difference(table.name, idx) for idx in table.indexes if idx.name
                )

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
                db_type_str = self._db_pg_type(db_col['type'])

                if model_col.computed is not None:
                    continue  # generated columns are defined by their expression; never ALTER them
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
                indexes_to_add.append(self._index_difference(table_name, model_indexes[idx_name]))

        required = set(self.metadata.info.get("required_extensions", []))
        extensions_to_add = sorted(required - self._installed_extensions()) if required else []

        return SchemaDiff(
            tables_to_add=tables_to_add, tables_to_drop=tables_to_drop,
            columns_to_add=columns_to_add, columns_to_modify=columns_to_modify,
            columns_to_drop=columns_to_drop,
            indexes_to_add=indexes_to_add, indexes_to_drop=indexes_to_drop,
            extensions_to_add=extensions_to_add,
        )

    @staticmethod
    def _index_difference(table_name: str, idx) -> IndexDifference:
        """Describe a model Index (unique flag, USING method, operator classes) as an IndexDifference."""
        pg_opts = idx.dialect_options["postgresql"]
        return IndexDifference(
            table_name=table_name, index_name=idx.name, change_type='add',
            columns=[c.name for c in idx.columns],
            unique=bool(idx.unique),
            using=pg_opts.get("using"),
            ops=dict(pg_opts.get("ops") or {}),
        )
