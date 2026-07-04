"""
Migration configuration — reads from environment variables.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
AUTO_GENERATED_DIR = BASE_DIR / "auto_generated"

# Set AUTO_MIGRATE=true in .env to run pending migrations automatically on startup
AUTO_MIGRATE_ON_STARTUP = os.getenv("AUTO_MIGRATE", "false").lower() == "true"
