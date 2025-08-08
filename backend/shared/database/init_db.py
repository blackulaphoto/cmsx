"""
Database initialization script for Case Management Suite
Creates all necessary tables using SQLAlchemy ORM
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .models import Base
from .session import get_sync_engine
from backend.core.config import settings

logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database with all tables"""
    try:
        # Get the engine
        engine = get_sync_engine()
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        logger.info("Database tables created successfully")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result.fetchall()]
            logger.info(f"Created tables: {tables}")
            
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Database initialization error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during database initialization: {e}")
        raise

def drop_all_tables():
    """Drop all tables (use with caution)"""
    try:
        engine = get_sync_engine()
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Error dropping tables: {e}")
        raise

def check_database_health():
    """Check database health and connectivity"""
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        
        logger.info("Database health check passed")
        return True
    except SQLAlchemyError as e:
        logger.error(f"Database health check failed: {e}")
        return False

if __name__ == "__main__":
    # Initialize database when run directly
    init_database()
