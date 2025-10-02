#!/usr/bin/env python3
"""
Database Migration Runner for Visa Agency Tables
Safely applies additive migrations without affecting existing restaurant functionality
"""

import os
import sys
import logging
from pathlib import Path

# Add parent directory to path to import database modules
sys.path.append(str(Path(__file__).parent.parent))

from database import engine
from sqlalchemy import text
from config import MIA_VISA_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration(migration_file: str) -> bool:
    """
    Run a single migration file
    Returns True if successful, False otherwise
    """
    migration_path = Path(__file__).parent / migration_file
    
    if not migration_path.exists():
        logger.error(f"Migration file not found: {migration_path}")
        return False
    
    try:
        with open(migration_path, 'r') as f:
            migration_sql = f.read()
        
        logger.info(f"Running migration: {migration_file}")
        
        with engine.connect() as conn:
            # Execute migration in a transaction
            with conn.begin():
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
                
                for stmt in statements:
                    if stmt:
                        logger.debug(f"Executing: {stmt[:100]}...")
                        conn.execute(text(stmt))
        
        logger.info(f"Migration completed successfully: {migration_file}")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {migration_file} - {str(e)}")
        return False


def run_all_migrations() -> bool:
    """
    Run all pending migrations
    Returns True if all successful, False if any failed
    """
    if not MIA_VISA_ENABLED:
        logger.info("MIA_VISA_ENABLED is False - skipping visa migrations")
        return True
    
    logger.info("Starting visa agency migrations...")
    
    migrations = [
        "001_add_visa_tables.sql"
    ]
    
    success_count = 0
    for migration in migrations:
        if run_migration(migration):
            success_count += 1
        else:
            logger.error(f"Migration failed, stopping: {migration}")
            return False
    
    logger.info(f"All {success_count} migrations completed successfully!")
    return True


def rollback_migrations() -> bool:
    """
    Rollback visa migrations (for testing/development)
    WARNING: This will drop all visa tables and data
    """
    if not MIA_VISA_ENABLED:
        logger.info("MIA_VISA_ENABLED is False - no rollback needed")
        return True
    
    logger.warning("Rolling back visa migrations - THIS WILL DELETE ALL VISA DATA!")
    
    rollback_sql = """
    -- Drop visa tables in reverse dependency order
    DROP TABLE IF EXISTS visa_applications CASCADE;
    DROP TABLE IF EXISTS visa_leads CASCADE;
    DROP TABLE IF EXISTS visa_eligibilities CASCADE;
    DROP TABLE IF EXISTS visa_requirements CASCADE;
    DROP TABLE IF EXISTS visa_products CASCADE;
    DROP TABLE IF EXISTS catalogs CASCADE;
    DROP TABLE IF EXISTS policy_packs CASCADE;
    DROP TABLE IF EXISTS restaurant_extensions CASCADE;
    DROP TABLE IF EXISTS businesses CASCADE;
    
    -- Remove type column from restaurants (if safe)
    -- ALTER TABLE restaurants DROP COLUMN IF EXISTS type;
    """
    
    try:
        with engine.connect() as conn:
            with conn.begin():
                statements = [stmt.strip() for stmt in rollback_sql.split(';') if stmt.strip()]
                for stmt in statements:
                    if stmt:
                        logger.debug(f"Executing rollback: {stmt[:100]}...")
                        conn.execute(text(stmt))
        
        logger.info("Rollback completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Rollback failed: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run visa agency database migrations")
    parser.add_argument("--rollback", action="store_true", help="Rollback migrations (WARNING: deletes data)")
    parser.add_argument("--force", action="store_true", help="Force run even if MIA_VISA_ENABLED is False")
    
    args = parser.parse_args()
    
    if args.force:
        logger.info("Force flag set - running regardless of MIA_VISA_ENABLED")
        # Temporarily override the flag
        import config
        config.MIA_VISA_ENABLED = True
    
    if args.rollback:
        success = rollback_migrations()
    else:
        success = run_all_migrations()
    
    sys.exit(0 if success else 1)
