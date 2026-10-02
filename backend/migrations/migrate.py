"""
Migration CLI - Command-line interface for database migrations.

Usage (run from backend/):
    python -m migrations.migrate generate [name]  - Generate a migration from model changes
    python -m migrations.migrate apply            - Apply pending migrations
    python -m migrations.migrate status           - Show migration status
    python -m migrations.migrate dry-run          - Preview without applying
    python -m migrations.migrate up               - generate + apply in one step (used by deploy.sh)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # make `app` importable when run as a script

from app.core.config import settings
from app.db.base import Base
import app.models  # noqa: F401 — registers all models onto Base.metadata
from migrations.migration_manager import MigrationManager


def _get_manager() -> MigrationManager:
    """Build a MigrationManager for the configured database and all registered models."""
    return MigrationManager(settings.DATABASE_URL, Base.metadata)


def main():
    """Parse the command and run it."""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1].lower()
    manager = _get_manager()

    if command == "generate":
        migration_name = sys.argv[2] if len(sys.argv) > 2 else None
        result = manager.generate_migration(migration_name)
        if result:
            print(f"\nMigration file created: {result}")
            print("Review it, then run: python -m migrations.migrate apply")
        else:
            print("\nNo changes detected — database is up to date.")

    elif command == "apply":
        count = manager.apply_migrations(dry_run=False)
        print(f"\nApplied {count} migration(s).")

    elif command == "up":
        manager.generate_migration()
        count = manager.apply_migrations(dry_run=False)
        print(f"\nApplied {count} migration(s).")

    elif command == "status":
        status = manager.get_status()
        print("\nMigration Status:")
        print(f"  Total:   {status['total']}")
        print(f"  Applied: {status['applied']}")
        print(f"  Pending: {status['pending']}")
        for name in status["pending_migrations"]:
            print(f"  - pending: {name}")

    elif command == "dry-run":
        count = manager.apply_migrations(dry_run=True)
        print(f"\n{count} migration(s) would be applied.")

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)


def print_usage():
    """Print CLI help."""
    print(__doc__)


if __name__ == "__main__":
    main()
