"""
Migration Manager - Tracks, generates, and applies PostgreSQL schema migrations.
Same pattern as the reference implementation but PostgreSQL-native.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from sqlalchemy import create_engine, text, MetaData, inspect
from migrations.schema_comparator import SchemaComparator, SchemaDiff
from migrations.sql_generator import SQLGenerator


class MigrationManager:
    def __init__(self, database_url: str, metadata: MetaData, migrations_dir: str = None):
        """Set up engine, comparator, generator, and ensure tracking table exists."""
        self.database_url = database_url
        self.metadata = metadata
        self.engine = create_engine(database_url)

        if migrations_dir is None:
            migrations_dir = Path(__file__).parent / "auto_generated"

        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        self.comparator = SchemaComparator(self.engine, metadata)
        self.sql_generator = SQLGenerator()

        self._ensure_tracking_table()

    def _ensure_tracking_table(self):
        """Create schema_migrations table if it does not exist yet."""
        inspector = inspect(self.engine)
        if 'schema_migrations' in inspector.get_table_names():
            return

        with self.engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE schema_migrations (
                    id SERIAL PRIMARY KEY,
                    migration_name VARCHAR(255) NOT NULL UNIQUE,
                    applied_at TIMESTAMPTZ DEFAULT NOW(),
                    sql_content TEXT
                )
            """))
            conn.execute(text(
                "CREATE INDEX idx_migration_name ON schema_migrations (migration_name)"
            ))

    def generate_migration(self, migration_name: Optional[str] = None) -> Optional[str]:
        """Compare models vs DB, write a .sql file for any differences, return its path."""
        diff = self.comparator.compare_schemas()

        if not diff.has_changes():
            print("No schema changes detected.")
            return None

        sql_statements = self.sql_generator.generate_migration_sql(diff, self.metadata)

        if not sql_statements:
            print("No SQL statements generated.")
            return None

        if migration_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            migration_name = f"{timestamp}_auto_migration"

        migration_file = self.migrations_dir / f"{migration_name}.sql"

        with open(migration_file, 'w') as f:
            f.write(f"-- Migration: {migration_name}\n")
            f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
            for sql in sql_statements:
                f.write(sql + "\n\n")

        print(f"[OK] Migration generated: {migration_file}")
        self._print_diff_summary(diff)
        return str(migration_file)

    def apply_migrations(self, dry_run: bool = False) -> int:
        """Apply all pending .sql files in order; return the count applied."""
        pending = self._get_pending_migrations()

        if not pending:
            print("No pending migrations.")
            return 0

        applied = 0
        for migration_file in pending:
            if dry_run:
                print(f"[DRY RUN] Would apply: {migration_file.name}")
                continue
            try:
                self._apply_migration(migration_file)
                applied += 1
                print(f"[OK] Applied: {migration_file.name}")
            except Exception as e:
                print(f"[ERROR] Failed to apply {migration_file.name}: {e}")
                raise

        return applied

    def _get_pending_migrations(self) -> List[Path]:
        """Return migration files that have not been recorded in schema_migrations."""
        all_files = sorted(self.migrations_dir.glob("*.sql"))

        with self.engine.connect() as conn:
            result = conn.execute(text("SELECT migration_name FROM schema_migrations"))
            applied = {row[0] for row in result}

        return [f for f in all_files if f.stem not in applied]

    def _apply_migration(self, migration_file: Path):
        """Execute every statement in the SQL file and record it as applied."""
        with open(migration_file, 'r') as f:
            sql_content = f.read()

        # Strip comment lines, split on semicolons
        lines = [l for l in sql_content.splitlines() if not l.strip().startswith('--')]
        statements = [s.strip() for s in '\n'.join(lines).split(';') if s.strip()]

        with self.engine.begin() as conn:
            for i, stmt in enumerate(statements):
                print(f"   Executing ({i+1}/{len(statements)}): {stmt[:80]}...")
                conn.execute(text(stmt))

            conn.execute(
                text("INSERT INTO schema_migrations (migration_name, sql_content) VALUES (:name, :content)"),
                {"name": migration_file.stem, "content": sql_content}
            )

        print("   Migration committed and recorded.")

    def get_status(self) -> dict:
        """Return a summary of applied and pending migrations."""
        all_files = sorted(self.migrations_dir.glob("*.sql"))

        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT migration_name, applied_at FROM schema_migrations ORDER BY applied_at")
            )
            applied = {row[0]: str(row[1]) for row in result}

        return {
            "total": len(all_files),
            "applied": len(applied),
            "pending": len(all_files) - len(applied),
            "applied_migrations": applied,
            "pending_migrations": [f.stem for f in all_files if f.stem not in applied],
        }

    def _print_diff_summary(self, diff: SchemaDiff):
        """Log a human-readable summary of detected schema differences."""
        print("\n[INFO] Schema changes detected:")
        if diff.tables_to_add:
            for t in diff.tables_to_add:
                print(f"  [+] Table: {t.table_name}")
        if diff.columns_to_add:
            for c in diff.columns_to_add:
                print(f"  [+] Column: {c.table_name}.{c.column_name}")
        if diff.columns_to_modify:
            for c in diff.columns_to_modify:
                print(f"  [~] Modify: {c.table_name}.{c.column_name}")
        if diff.indexes_to_add:
            for i in diff.indexes_to_add:
                print(f"  [+] Index: {i.table_name}.{i.index_name}")
        print()
