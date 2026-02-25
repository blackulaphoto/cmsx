"""
Database session management for Case Management Suite using SQLAlchemy
"""

import logging
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

logger = logging.getLogger(__name__)

# Global engine and session factory
_async_engine = None
_async_session_factory = None
_sync_engine = None
_sync_session_factory = None

def get_async_engine():
    """Get or create async engine"""
    global _async_engine
    if _async_engine is None:
        from backend.core.config import settings
        db_url = settings.database.url
        # Convert sync URLs to async driver URLs.
        if db_url.startswith("sqlite:///"):
            db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        _async_engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=300
        )
    return _async_engine

def get_sync_engine():
    """Get or create sync engine"""
    global _sync_engine
    if _sync_engine is None:
        from backend.core.config import settings
        _sync_engine = create_engine(
            settings.database.url,
            echo=False,  # Set to True for SQL debugging
            pool_pre_ping=True,
            pool_recycle=300
        )
    return _sync_engine

def get_async_session_factory():
    """Get or create async session factory"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    return _async_session_factory

def get_sync_session_factory():
    """Get or create sync session factory"""
    global _sync_session_factory
    if _sync_session_factory is None:
        engine = get_sync_engine()
        _sync_session_factory = sessionmaker(
            engine,
            expire_on_commit=False
        )
    return _sync_session_factory

@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session context manager using SQLAlchemy.
    This provides a proper async session with full SQLAlchemy ORM capabilities.
    """
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()

def get_session():
    """
    Get a synchronous database session context manager.
    This is a simplified version that works with our SQLite setup.
    """
    session_factory = get_sync_session_factory()
    with session_factory() as session:
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

async def init_db():
    """Initialize database tables"""
    from backend.shared.database.models import Base
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")

async def close_db():
    """Close database connections"""
    global _async_engine, _sync_engine
    if _async_engine:
        await _async_engine.dispose()
        _async_engine = None
    if _sync_engine:
        _sync_engine.dispose()
        _sync_engine = None
    logger.info("Database connections closed") 
