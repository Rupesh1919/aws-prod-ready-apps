#!/usr/bin/env python3
"""Run database migrations using Alembic."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from alembic import command
from alembic.config import Config

from claims_api.core.logging import get_logger, setup_logging

setup_logging()
logger = get_logger("migrate")


def run_migrations() -> None:
    """Run Alembic migrations to upgrade database to latest version."""
    try:
        logger.info("Starting database migrations")
        
        # Load Alembic configuration
        alembic_cfg = Config("alembic.ini")
        
        # Run migrations
        command.upgrade(alembic_cfg, "head")
        
        logger.info("Database migrations completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
