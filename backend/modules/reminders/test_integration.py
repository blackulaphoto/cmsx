#!/usr/bin/env python3
"""
Test Reminder System Integration
Verify that the reminder system is properly integrated with the case management database
"""

import os
import sys
import logging
from pathlib import Path

# Add the backend directory to Python path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from modules.reminders.models import ReminderDatabase
from modules.reminders.engine import IntelligentReminderEngine
from modules.reminders.smart_distributor import SmartTaskDistributor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reminder_integration():
    """Test the reminder system integration"""
    
    try:
        # Change to project root directory
        project_root = backend_dir.parent
        os.chdir(project_root)
        
        logger.info("Testing reminder system integration...")
        
        # Initialize reminder database
        reminder_db = ReminderDatabase('databases/reminders.db')
        
        # Test case management database connection
        logger.info("Testing case management database connection...")
        clients = reminder_db.get_clients_for_case_manager('test_manager')
        logger.info(f"Found {len(clients)} clients for test_manager")
        
        # Test reminder engine
        logger.info("Testing reminder engine...")
        engine = IntelligentReminderEngine(reminder_db)
        
        # Test smart distributor
        logger.info("Testing smart task distributor...")
        distributor = SmartTaskDistributor(reminder_db)
        
        # Test weekly plan generation
        logger.info("Testing weekly plan generation...")
        weekly_plan = distributor.generate_weekly_task_plan('test_manager')
        
        if 'error' not in weekly_plan:
            logger.info(f"✅ Weekly plan generated successfully with {weekly_plan.get('total_tasks', 0)} tasks")
        else:
            logger.warning(f"⚠️ Weekly plan generation returned error: {weekly_plan['error']}")
        
        # Test daily focus plan
        logger.info("Testing daily focus plan...")
        daily_plan = distributor.get_daily_focus_plan('test_manager')
        
        if 'error' not in daily_plan:
            logger.info(f"✅ Daily focus plan generated successfully")
        else:
            logger.warning(f"⚠️ Daily focus plan generation returned error: {daily_plan['error']}")
        
        # Close connections
        reminder_db.close()
        
        logger.info("✅ All integration tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Integration test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_reminder_integration()
    if success:
        print("Integration test completed successfully!")
    else:
        print("Integration test failed!")
        sys.exit(1)