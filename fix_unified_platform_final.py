#!/usr/bin/env python3
"""
Final fix for unified_platform database
"""

import sqlite3
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_unified_platform():
    """Fix the remaining unified_platform issues"""
    
    db_path = 'databases/unified_platform.db'
    backup_path = f"{db_path}.backup_final_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    try:
        # Create backup
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"✅ Created backup: {backup_path}")
        
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys = OFF")
        cursor = conn.cursor()
        
        # Check what clients table exists (if any)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='clients'")
        clients_exists = cursor.fetchone() is not None
        
        if clients_exists:
            # Get valid client IDs
            cursor.execute("SELECT id FROM clients")
            valid_clients = {row[0] for row in cursor.fetchall()}
            logger.info(f"Found {len(valid_clients)} valid clients")
            
            if valid_clients:
                # Remove benefits_applications with invalid client_id
                placeholders = ','.join('?' * len(valid_clients))
                cursor.execute(f"""
                    DELETE FROM benefits_applications 
                    WHERE client_id NOT IN ({placeholders})
                """, list(valid_clients))
                deleted = cursor.rowcount
                logger.info(f"Removed {deleted} benefit applications with invalid client_id")
            else:
                # No valid clients, remove all
                cursor.execute("DELETE FROM benefits_applications")
                deleted = cursor.rowcount
                logger.info(f"Removed {deleted} benefit applications (no valid clients)")
        else:
            # No clients table, remove all benefit applications
            cursor.execute("DELETE FROM benefits_applications")
            deleted = cursor.rowcount
            logger.info(f"Removed {deleted} benefit applications (no clients table)")
        
        conn.commit()
        
        # Verify fix
        cursor.execute("PRAGMA foreign_key_check")
        violations = cursor.fetchall()
        
        conn.close()
        
        if len(violations) == 0:
            logger.info("✅ All foreign key violations fixed!")
            return True
        else:
            logger.warning(f"⚠️ {len(violations)} violations still remain")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to fix unified_platform: {e}")
        return False

if __name__ == "__main__":
    success = fix_unified_platform()
    exit(0 if success else 1)