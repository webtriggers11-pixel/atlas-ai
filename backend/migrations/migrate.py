"""
Migration CLI - Command-line interface for database migrations

Usage (run from project root):
    python -m app.migrations.migrate generate [name]  - Generate migration from model changes
    python -m app.migrations.migrate apply            - Apply pending migrations
    python -m app.migrations.migrate status           - Show migration status
    python -m app.migrations.migrate dry-run          - Preview without applying
"""
import sys
from pathlib import Path

# Allow running from project root: python -m app.migrations.migrate
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.migrations.migration_manager import MigrationManager
from app.migrations.config import get_database_url
from app.db.database import Base
import app.models  # noqa: F401 — registers all models onto Base.metadata


def _get_manager() -> MigrationManager:
    return MigrationManager(get_database_url(), Base.metadata)


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "generate":
        manager = _get_manager()
        migration_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = manager.generate_migration(migration_name)
        if result:
            print(f"\nMigration file created: {result}")
            print("\nTo apply this migration run:")
            print("  python -m app.migrations.migrate apply")
        else:
            print("\nNo changes detected — database is up to date.")

    elif command == "apply":
        manager = _get_manager()
        print("Applying pending migrations...\n")
        count = manager.apply_migrations(dry_run=False)
        if count > 0:
            print(f"\nSuccessfully applied {count} migration(s).")
        else:
            print("\nNo pending migrations to apply.")

    elif command == "status":
        manager = _get_manager()
        status = manager.get_migration_status()
        print("\nMigration Status:")
        print(f"  Total:   {status['total_migrations']}")
        print(f"  Applied: {status['applied_count']}")
        print(f"  Pending: {status['pending_count']}")

        if status["applied_migrations"]:
            print("\nApplied:")
            for name, applied_at in status["applied_migrations"].items():
                print(f"  + {name}  (applied: {applied_at})")

        if status["pending_migrations"]:
            print("\nPending:")
            for name in status["pending_migrations"]:
                print(f"  - {name}")
        print()

    elif command == "dry-run":
        manager = _get_manager()
        print("Dry run — showing what would be applied...\n")
        count = manager.apply_migrations(dry_run=True)
        print(f"\n{count} migration(s) would be applied.")

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


def print_usage():
    print("""
Migration CLI

Usage (from project root):
    python -m app.migrations.migrate <command> [options]

Commands:
    generate [name]  Generate a new migration based on model changes
    apply            Apply all pending migrations
    status           Show migration status
    dry-run          Preview what would be applied (no changes made)

Examples:
    python -m app.migrations.migrate generate
    python -m app.migrations.migrate generate add_users_table
    python -m app.migrations.migrate apply
    python -m app.migrations.migrate status
    """)


if __name__ == "__main__":
    main()
