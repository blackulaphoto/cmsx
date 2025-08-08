#!/usr/bin/env python3
"""
Database initialization script for Case Management Suite
"""

import asyncio
import logging
from backend.shared.database.session import init_db, close_db
from backend.shared.database.models import Base, Task, Client, User

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Initialize the database with tables"""
    try:
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialization completed successfully!")
        
        # Optional: Add some sample data for testing
        await add_sample_data()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        await close_db()

async def add_sample_data():
    """Add sample data for testing"""
    try:
        from backend.shared.database.session import get_async_session
        from backend.shared.database.models import TaskPriority, TaskStatus
        from datetime import datetime, timezone, timedelta
        from uuid import uuid4
        
        async with get_async_session() as session:
            # Add sample client
            client = Client(
                id="client_123",
                first_name="John",
                last_name="Doe",
                email="john.doe@example.com",
                phone="555-123-4567",
                status="active"
            )
            session.add(client)
            
            # Add sample user
            user = User(
                id="user_456",
                username="case_manager_1",
                email="case_manager@example.com",
                role="case_manager"
            )
            session.add(user)
            
            # Add sample task
            task = Task(
                id="task_123",
                client_id="client_123",
                title="Apply for housing assistance",
                description="Complete housing application and submit required documents",
                priority=TaskPriority.HIGH,
                status=TaskStatus.PENDING,
                due_date=datetime.now(timezone.utc) + timedelta(days=7),
                category="housing",
                task_type="manual",
                assigned_to="user_456",
                created_by="user_456",
                ai_generated=False,
                ai_priority_score=0.8
            )
            session.add(task)
            
            await session.commit()
            logger.info("Sample data added successfully!")
            
    except Exception as e:
        logger.error(f"Error adding sample data: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 