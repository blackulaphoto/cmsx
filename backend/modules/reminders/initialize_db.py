#!/usr/bin/env python3
"""
Initialize Reminder Database
Set up the reminder system database with all necessary tables and default data
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from modules.reminders.models import ReminderDatabase
from modules.reminders.process_models import ProcessDatabase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_reminder_system():
    """Initialize the complete reminder system database"""
    
    try:
        # Change to project root directory
        project_root = backend_dir.parent
        os.chdir(project_root)
        
        logger.info("Initializing reminder system database...")
        
        # Create reminder database
        reminder_db = ReminderDatabase('databases/reminders.db')
        
        # Create process database (which also creates process tables)
        process_db = ProcessDatabase(reminder_db)
        
        logger.info("✅ Reminder system database initialized successfully")
        
        # Test the connection to case management database
        logger.info("Testing case management database connection...")
        test_clients = reminder_db.get_clients_for_case_manager('test_manager')
        logger.info(f"✅ Case management connection successful (found {len(test_clients)} clients for test)")
        
        # Close connections
        reminder_db.close()
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize reminder system: {e}")
        return False

if __name__ == "__main__":
    success = initialize_reminder_system()
    if success:
        print("🎉 Reminder system database initialization complete!")
    else:
        print("💥 Reminder system initialization failed!")
        sys.exit(1)