#!/usr/bin/env python3
"""
Real Data Integration for Reminders System
Connects reminders to actual client data and module information
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .models import ReminderDatabase

logger = logging.getLogger(__name__)

class RealDataIntegrator:
    """Integrates real data from databases into reminders system"""
    
    def __init__(self):
        self.reminder_db = ReminderDatabase()
        self.case_mgmt_db_path = 'databases/case_management.db'
    
    def get_smart_dashboard_data(self, case_manager_id: str) -> Dict[str, Any]:
        """Get real dashboard data for case manager"""
        try:
            # Get active reminders
            active_reminders = self.get_active_reminders(case_manager_id)
            
            # Get client workload
            client_workload = self.get_client_workload(case_manager_id)
            
            # Get today's tasks
            today_tasks = self.get_today_tasks(case_manager_id)
            
            # Calculate workload metrics
            workload_summary = self.calculate_workload_summary(active_reminders, today_tasks)
            
            # Generate AI recommendations
            recommendations = self.generate_ai_recommendations(active_reminders, client_workload)
            
            dashboard_data = {
                'case_manager_id': case_manager_id,
                'generated_at': datetime.now().isoformat(),
                'daily_focus': self.generate_daily_focus(active_reminders),
                'workload_summary': workload_summary,
                'today_tasks': today_tasks,
                'urgent_items': [r for r in active_reminders if r['priority'] in ['Critical', 'High']],
                'recommendations': recommendations,
                'client_summary': client_workload
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting smart dashboard data: {e}")
            return self.get_fallback_dashboard_data(case_manager_id)
    
    def get_active_reminders(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get active reminders for case manager"""
        try:
            cursor = self.reminder_db.connection.cursor()
            # First get reminders from reminders database
            cursor.execute("""
                SELECT 
                    reminder_id,
                    client_id,
                    reminder_type,
                    message,
                    priority,
                    due_date,
                    status,
                    created_at
                FROM active_reminders
                WHERE case_manager_id = ? 
                AND status = 'Active'
                ORDER BY 
                    CASE priority 
                        WHEN 'Critical' THEN 1
                        WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3
                        ELSE 4
                    END,
                    due_date
            """, (case_manager_id,))
            
            reminders = []
            for row in cursor.fetchall():
                # Get client name from case management database
                client_name = self.get_client_name(row[1])
                
                reminders.append({
                    'reminder_id': row[0],
                    'client_id': row[1],
                    'type': row[2],
                    'message': row[3],
                    'priority': row[4],
                    'due_date': row[5],
                    'status': row[6],
                    'created_at': row[7],
                    'client_name': client_name,
                    'risk_level': 'medium'  # Default for now
                })
            
            return reminders
            
        except Exception as e:
            logger.error(f"Error getting active reminders: {e}")
            return []
    
    def get_client_workload(self, case_manager_id: str) -> Dict[str, Any]:
        """Get client workload summary for case manager"""
        try:
            # Connect to case management database
            conn = sqlite3.connect(self.case_mgmt_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get client counts by risk level
            cursor.execute("""
                SELECT 
                    risk_level,
                    COUNT(*) as count
                FROM clients 
                WHERE case_manager_id = ? AND case_status = 'Active' AND is_active = 1
                GROUP BY risk_level
            """, (case_manager_id,))
            
            risk_counts = {row['risk_level']: row['count'] for row in cursor.fetchall()}
            
            # Get total clients
            cursor.execute("""
                SELECT COUNT(*) as total
                FROM clients 
                WHERE case_manager_id = ? AND case_status = 'Active' AND is_active = 1
            """, (case_manager_id,))
            
            total_clients = cursor.fetchone()['total']
            
            # Get recent contacts
            cursor.execute("""
                SELECT COUNT(*) as recent_contacts
                FROM client_contacts cc
                JOIN clients c ON cc.client_id = c.client_id
                WHERE cc.case_manager_id = ? 
                AND date(cc.contact_date) >= date('now', '-7 days')
                AND c.is_active = 1
            """, (case_manager_id,))
            
            recent_contacts = cursor.fetchone()['recent_contacts']
            
            conn.close()
            
            return {
                'total_clients': total_clients,
                'high_risk': risk_counts.get('high', 0),
                'medium_risk': risk_counts.get('medium', 0),
                'low_risk': risk_counts.get('low', 0),
                'recent_contacts': recent_contacts
            }
            
        except Exception as e:
            logger.error(f"Error getting client workload: {e}")
            return {'total_clients': 0, 'high_risk': 0, 'medium_risk': 0, 'low_risk': 0, 'recent_contacts': 0}
    
    def get_today_tasks(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get today's tasks for case manager"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    t.id,
                    t.client_id,
                    t.title,
                    t.description,
                    t.due_date,
                    t.priority,
                    t.status,
                    t.category,
                    t.task_type,
                    c.first_name || ' ' || c.last_name as client_name
                FROM tasks t
                LEFT JOIN clients c ON t.client_id = c.client_id
                WHERE t.assigned_to = ?
                AND date(t.due_date) <= date('now', '+1 day')
                AND t.status != 'completed'
                ORDER BY 
                    CASE t.priority 
                        WHEN 'Critical' THEN 1
                        WHEN 'High' THEN 2
                        WHEN 'Medium' THEN 3
                        ELSE 4
                    END,
                    t.due_date
            """, (case_manager_id,))
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'task_id': f"task_{row['id']}",
                    'client_id': row['client_id'],
                    'client_name': row['client_name'] or 'Unknown Client',
                    'title': row['title'],
                    'description': row['description'],
                    'task_type': row['task_type'] or row['category'],
                    'priority': row['priority'],
                    'status': row['status'],
                    'due_date': row['due_date'],
                    'estimated_minutes': 60  # Default estimate
                })
            
            conn.close()
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting today's tasks: {e}")
            return []
    
    def calculate_workload_summary(self, reminders: List[Dict], tasks: List[Dict]) -> Dict[str, Any]:
        """Calculate workload summary metrics"""
        urgent_reminders = len([r for r in reminders if r['priority'] in ['Critical', 'High']])
        urgent_tasks = len([t for t in tasks if t['priority'] in ['Critical', 'High']])
        
        total_estimated_minutes = sum(t.get('estimated_minutes', 60) for t in tasks)
        
        # Calculate capacity utilization (assuming 8-hour workday = 480 minutes)
        capacity_utilization = min(100, int((total_estimated_minutes / 480) * 100))
        
        return {
            'total_tasks': len(tasks),
            'urgent_tasks': urgent_tasks,
            'total_reminders': len(reminders),
            'urgent_reminders': urgent_reminders,
            'today_estimated_minutes': total_estimated_minutes,
            'capacity_utilization': capacity_utilization
        }
    
    def generate_daily_focus(self, reminders: List[Dict]) -> str:
        """Generate daily focus message based on reminders"""
        if not reminders:
            return "No urgent items today - focus on proactive client outreach"
        
        critical_count = len([r for r in reminders if r['priority'] == 'Critical'])
        high_count = len([r for r in reminders if r['priority'] == 'High'])
        
        if critical_count > 0:
            return f"URGENT: {critical_count} critical items require immediate attention"
        elif high_count > 0:
            return f"Priority focus: {high_count} high-priority items need attention today"
        else:
            return "Routine day - focus on client check-ins and documentation"
    
    def generate_ai_recommendations(self, reminders: List[Dict], workload: Dict) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        # High-risk client recommendations
        if workload.get('high_risk', 0) > 0:
            recommendations.append(f"Prioritize contact with {workload['high_risk']} high-risk clients")
        
        # Workload management
        if workload.get('capacity_utilization', 0) > 90:
            recommendations.append("Consider delegating non-critical tasks - workload at capacity")
        elif workload.get('capacity_utilization', 0) < 50:
            recommendations.append("Capacity available for proactive client outreach")
        
        # Contact frequency
        if workload.get('recent_contacts', 0) < workload.get('total_clients', 0) * 0.3:
            recommendations.append("Increase client contact frequency - many clients haven't been contacted recently")
        
        # Reminder-based recommendations
        critical_reminders = [r for r in reminders if r['priority'] == 'Critical']
        if critical_reminders:
            recommendations.append(f"Address {len(critical_reminders)} critical reminders immediately")
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def get_real_tasks_data(self, case_manager_id: str = None, status: str = None, client_id: str = None) -> List[Dict[str, Any]]:
        """Get real tasks data from database"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build query with filters
            query = """
                SELECT 
                    t.id,
                    t.client_id,
                    t.title,
                    t.description,
                    t.due_date,
                    t.priority,
                    t.status,
                    t.category,
                    t.task_type,
                    t.assigned_to,
                    t.created_at,
                    c.first_name || ' ' || c.last_name as client_name
                FROM tasks t
                LEFT JOIN clients c ON t.client_id = c.client_id
                WHERE 1=1
            """
            
            params = []
            
            if case_manager_id:
                query += " AND t.assigned_to = ?"
                params.append(case_manager_id)
            
            if status:
                query += " AND t.status = ?"
                params.append(status)
            
            if client_id:
                query += " AND t.client_id = ?"
                params.append(client_id)
            
            query += " ORDER BY t.due_date, t.priority"
            
            cursor.execute(query, params)
            
            tasks = []
            for row in cursor.fetchall():
                tasks.append({
                    'task_id': f"task_{row['id']}",
                    'client_id': row['client_id'],
                    'client_name': row['client_name'] or 'Unknown Client',
                    'title': row['title'],
                    'description': row['description'],
                    'task_type': row['task_type'] or row['category'],
                    'priority': row['priority'],
                    'status': row['status'],
                    'due_date': row['due_date'],
                    'estimated_minutes': 60,
                    'created_at': row['created_at']
                })
            
            conn.close()
            return tasks
            
        except Exception as e:
            logger.error(f"Error getting real tasks data: {e}")
            return []
    
    def get_fallback_dashboard_data(self, case_manager_id: str) -> Dict[str, Any]:
        """Fallback dashboard data if real data fails"""
        return {
            'case_manager_id': case_manager_id,
            'generated_at': datetime.now().isoformat(),
            'daily_focus': 'System initializing - please check back shortly',
            'workload_summary': {
                'total_tasks': 0,
                'urgent_tasks': 0,
                'today_estimated_minutes': 0,
                'capacity_utilization': 0
            },
            'today_tasks': [],
            'recommendations': ['System is loading real data - please refresh in a moment'],
            'urgent_items': []
        }
    
    def get_client_name(self, client_id: str) -> str:
        """Get client name from case management database"""
        try:
            conn = sqlite3.connect(self.case_mgmt_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT first_name || ' ' || last_name as client_name
                FROM clients 
                WHERE client_id = ?
            """, (client_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else 'Unknown Client'
            
        except Exception as e:
            logger.error(f"Error getting client name: {e}")
            return 'Unknown Client'
    
    def close(self):
        """Close database connections"""
        if self.reminder_db:
            self.reminder_db.close()