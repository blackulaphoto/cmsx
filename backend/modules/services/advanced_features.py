#!/usr/bin/env python3
"""
Advanced Analytics and Communication Features for Social Services
Phase 3 implementation: Advanced analytics, communication system, and workflow automation
"""

import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
import uuid
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

class CommunicationLog:
    """Communication log for provider interactions"""
    
    def __init__(self, **kwargs):
        self.id = kwargs.get('id')
        self.communication_id = kwargs.get('communication_id', str(uuid.uuid4()))
        self.case_manager_id = kwargs.get('case_manager_id', '')
        self.provider_id = kwargs.get('provider_id', '')
        self.client_id = kwargs.get('client_id', '')
        self.referral_id = kwargs.get('referral_id', '')
        
        # Communication Details
        self.communication_type = kwargs.get('communication_type', 'Email')  # Email, Phone, In-Person, Secure Message
        self.direction = kwargs.get('direction', 'Outbound')  # Outbound, Inbound
        self.subject = kwargs.get('subject', '')
        self.content = kwargs.get('content', '')
        self.priority = kwargs.get('priority', 'Normal')  # Low, Normal, High, Urgent
        
        # Participants
        self.to_contacts = kwargs.get('to_contacts', '')  # JSON string of contact list
        self.cc_contacts = kwargs.get('cc_contacts', '')
        self.from_contact = kwargs.get('from_contact', '')
        
        # Status and Tracking
        self.status = kwargs.get('status', 'Sent')  # Draft, Sent, Delivered, Read, Replied
        self.read_date = kwargs.get('read_date', '')
        self.reply_date = kwargs.get('reply_date', '')
        self.follow_up_required = kwargs.get('follow_up_required', False)
        self.follow_up_date = kwargs.get('follow_up_date', '')
        
        # Attachments and References
        self.attachments = kwargs.get('attachments', '')  # JSON string of attachment list
        self.related_documents = kwargs.get('related_documents', '')
        self.tags = kwargs.get('tags', '')  # JSON string of tags
        
        # Metadata
        self.created_at = kwargs.get('created_at', datetime.now().isoformat())
        self.created_by = kwargs.get('created_by', '')
        self.is_confidential = kwargs.get('is_confidential', True)
        self.is_archived = kwargs.get('is_archived', False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': self.id,
            'communication_id': self.communication_id,
            'case_manager_id': self.case_manager_id,
            'provider_id': self.provider_id,
            'client_id': self.client_id,
            'referral_id': self.referral_id,
            'communication_type': self.communication_type,
            'direction': self.direction,
            'subject': self.subject,
            'content': self.content,
            'priority': self.priority,
            'to_contacts': self.to_contacts,
            'cc_contacts': self.cc_contacts,
            'from_contact': self.from_contact,
            'status': self.status,
            'read_date': self.read_date,
            'reply_date': self.reply_date,
            'follow_up_required': self.follow_up_required,
            'follow_up_date': self.follow_up_date,
            'attachments': self.attachments,
            'related_documents': self.related_documents,
            'tags': self.tags,
            'created_at': self.created_at,
            'created_by': self.created_by,
            'is_confidential': self.is_confidential,
            'is_archived': self.is_archived
        }


class PerformanceMetrics:
    """Performance metrics and analytics for case management"""
    
    def __init__(self, db_path: str = "social_services.db"):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Connect to database"""
        if not self.connection:
            # Use check_same_thread=False for Flask threading compatibility
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
    
    def get_case_manager_performance(self, case_manager_id: str, period_days: int = 30) -> Dict[str, Any]:
        """Get comprehensive performance metrics for a case manager"""
        self.connect()
        
        start_date = (datetime.now() - timedelta(days=period_days)).isoformat()
        
        try:
            cursor = self.connection.cursor()
            
            # Client metrics
            cursor.execute("""
                SELECT COUNT(*) as active_clients,
                       AVG(CASE WHEN risk_level = 'High' THEN 3 WHEN risk_level = 'Medium' THEN 2 ELSE 1 END) as avg_risk_score,
                       SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_clients
                FROM clients 
                WHERE case_manager_id = ? AND is_active = 1
            """, (case_manager_id,))
            client_metrics = dict(cursor.fetchone())
            
            # Referral metrics
            cursor.execute("""
                SELECT COUNT(*) as total_referrals,
                       SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                       SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_referrals,
                       AVG(julianday('now') - julianday(referral_date)) as avg_referral_age_days,
                       SUM(CASE WHEN priority_level = 'High' OR priority_level = 'Urgent' THEN 1 ELSE 0 END) as high_priority_referrals
                FROM service_referrals 
                WHERE case_manager_id = ? AND referral_date >= ?
            """, (case_manager_id, start_date))
            referral_metrics = dict(cursor.fetchone())
            
            # Task metrics
            cursor.execute("""
                SELECT COUNT(*) as total_tasks,
                       SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tasks,
                       SUM(CASE WHEN due_date < datetime('now') AND status != 'Completed' THEN 1 ELSE 0 END) as overdue_tasks,
                       AVG(time_spent_minutes) as avg_task_time_minutes
                FROM case_management_tasks 
                WHERE case_manager_id = ? AND created_at >= ?
            """, (case_manager_id, start_date))
            task_metrics = dict(cursor.fetchone())
            
            # Communication metrics
            cursor.execute("""
                SELECT COUNT(*) as total_communications,
                       SUM(CASE WHEN direction = 'Outbound' THEN 1 ELSE 0 END) as outbound_communications,
                       SUM(CASE WHEN follow_up_required = 1 THEN 1 ELSE 0 END) as follow_ups_required
                FROM communication_logs 
                WHERE case_manager_id = ? AND created_at >= ?
            """, (case_manager_id, start_date))
            communication_metrics = dict(cursor.fetchone()) if cursor.fetchone() else {}
            
            # Calculate success rates
            referral_success_rate = 0
            if referral_metrics['total_referrals'] > 0:
                referral_success_rate = (referral_metrics['completed_referrals'] / referral_metrics['total_referrals']) * 100
            
            task_completion_rate = 0
            if task_metrics['total_tasks'] > 0:
                task_completion_rate = (task_metrics['completed_tasks'] / task_metrics['total_tasks']) * 100
            
            return {
                'period_days': period_days,
                'client_metrics': client_metrics,
                'referral_metrics': referral_metrics,
                'task_metrics': task_metrics,
                'communication_metrics': communication_metrics,
                'calculated_metrics': {
                    'referral_success_rate': referral_success_rate,
                    'task_completion_rate': task_completion_rate,
                    'avg_referrals_per_client': referral_metrics['total_referrals'] / max(client_metrics['active_clients'], 1),
                    'avg_tasks_per_client': task_metrics['total_tasks'] / max(client_metrics['active_clients'], 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    def get_provider_performance_analysis(self, provider_id: str = None) -> Dict[str, Any]:
        """Get provider network performance analysis"""
        self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            if provider_id:
                # Specific provider analysis
                cursor.execute("""
                    SELECT p.name, p.provider_id, p.organization_type,
                           COUNT(r.referral_id) as total_referrals,
                           SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                           SUM(CASE WHEN r.status = 'Active' THEN 1 ELSE 0 END) as active_referrals,
                           AVG(r.satisfaction_rating) as avg_satisfaction,
                           AVG(julianday(r.completion_date) - julianday(r.referral_date)) as avg_completion_days
                    FROM service_providers p
                    LEFT JOIN service_referrals r ON p.provider_id = r.provider_id
                    WHERE p.provider_id = ?
                    GROUP BY p.provider_id
                """, (provider_id,))
                
                provider_data = dict(cursor.fetchone())
                
                # Get recent referrals
                cursor.execute("""
                    SELECT r.referral_id, r.status, r.priority_level, r.referral_date,
                           c.first_name, c.last_name, s.service_category
                    FROM service_referrals r
                    JOIN clients c ON r.client_id = c.client_id
                    JOIN social_services s ON r.service_id = s.service_id
                    WHERE r.provider_id = ?
                    ORDER BY r.referral_date DESC
                    LIMIT 10
                """, (provider_id,))
                
                recent_referrals = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'provider_data': provider_data,
                    'recent_referrals': recent_referrals
                }
            else:
                # Network-wide analysis
                cursor.execute("""
                    SELECT p.name, p.provider_id, p.organization_type,
                           COUNT(r.referral_id) as total_referrals,
                           SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                           AVG(r.satisfaction_rating) as avg_satisfaction,
                           p.success_rate, p.completion_rate, p.client_satisfaction
                    FROM service_providers p
                    LEFT JOIN service_referrals r ON p.provider_id = r.provider_id
                    GROUP BY p.provider_id
                    ORDER BY total_referrals DESC
                """)
                
                provider_analysis = [dict(row) for row in cursor.fetchall()]
                
                return {
                    'provider_analysis': provider_analysis,
                    'network_summary': {
                        'total_providers': len(provider_analysis),
                        'avg_referrals_per_provider': statistics.mean([p['total_referrals'] for p in provider_analysis if p['total_referrals']]),
                        'top_providers': sorted(provider_analysis, key=lambda x: x['total_referrals'], reverse=True)[:5]
                    }
                }
                
        except Exception as e:
            logger.error(f"Error analyzing provider performance: {e}")
            return {}
    
    def get_service_gap_analysis(self) -> Dict[str, Any]:
        """Analyze service gaps and unmet needs"""
        self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Service demand analysis
            cursor.execute("""
                SELECT s.service_category, COUNT(r.referral_id) as referral_count,
                       SUM(CASE WHEN r.status = 'Pending' THEN 1 ELSE 0 END) as pending_referrals,
                       SUM(CASE WHEN r.status = 'Active' THEN 1 ELSE 0 END) as active_referrals,
                       AVG(julianday('now') - julianday(r.referral_date)) as avg_wait_time_days
                FROM social_services s
                LEFT JOIN service_referrals r ON s.service_id = r.service_id
                GROUP BY s.service_category
                ORDER BY referral_count DESC
            """)
            
            service_demand = [dict(row) for row in cursor.fetchall()]
            
            # Provider capacity analysis
            cursor.execute("""
                SELECT p.county, s.service_category, COUNT(s.service_id) as service_count,
                       SUM(p.total_capacity) as total_capacity,
                       SUM(p.current_capacity) as current_capacity,
                       AVG(p.waitlist_length) as avg_waitlist_length
                FROM service_providers p
                JOIN social_services s ON p.provider_id = s.provider_id
                GROUP BY p.county, s.service_category
                ORDER BY p.county, service_count DESC
            """)
            
            capacity_analysis = [dict(row) for row in cursor.fetchall()]
            
            # Identify gaps
            gaps = []
            for service in service_demand:
                if service['pending_referrals'] > 5:  # Threshold for gap identification
                    gaps.append({
                        'service_category': service['service_category'],
                        'pending_referrals': service['pending_referrals'],
                        'avg_wait_time': service['avg_wait_time_days'],
                        'gap_severity': 'High' if service['pending_referrals'] > 10 else 'Medium'
                    })
            
            return {
                'service_demand': service_demand,
                'capacity_analysis': capacity_analysis,
                'identified_gaps': gaps,
                'recommendations': self._generate_gap_recommendations(gaps)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing service gaps: {e}")
            return {}
    
    def _generate_gap_recommendations(self, gaps: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations based on service gaps"""
        recommendations = []
        
        for gap in gaps:
            if gap['gap_severity'] == 'High':
                recommendations.append(f"Urgent: Expand {gap['service_category']} capacity - {gap['pending_referrals']} pending referrals")
            else:
                recommendations.append(f"Consider expanding {gap['service_category']} services")
        
        return recommendations
    
    def get_outcome_trends(self, period_days: int = 90) -> Dict[str, Any]:
        """Analyze outcome trends over time"""
        self.connect()
        
        start_date = (datetime.now() - timedelta(days=period_days)).isoformat()
        
        try:
            cursor = self.connection.cursor()
            
            # Monthly outcome trends
            cursor.execute("""
                SELECT strftime('%Y-%m', completion_date) as month,
                       COUNT(*) as total_completions,
                       SUM(CASE WHEN outcome = 'Successful' THEN 1 ELSE 0 END) as successful_outcomes,
                       AVG(satisfaction_rating) as avg_satisfaction
                FROM service_referrals
                WHERE completion_date >= ? AND completion_date != ''
                GROUP BY strftime('%Y-%m', completion_date)
                ORDER BY month
            """, (start_date,))
            
            monthly_trends = [dict(row) for row in cursor.fetchall()]
            
            # Service category outcomes
            cursor.execute("""
                SELECT s.service_category,
                       COUNT(r.referral_id) as total_referrals,
                       SUM(CASE WHEN r.outcome = 'Successful' THEN 1 ELSE 0 END) as successful_outcomes,
                       AVG(r.satisfaction_rating) as avg_satisfaction
                FROM social_services s
                JOIN service_referrals r ON s.service_id = r.service_id
                WHERE r.completion_date >= ? AND r.completion_date != ''
                GROUP BY s.service_category
                ORDER BY successful_outcomes DESC
            """, (start_date,))
            
            category_outcomes = [dict(row) for row in cursor.fetchall()]
            
            return {
                'monthly_trends': monthly_trends,
                'category_outcomes': category_outcomes,
                'period_days': period_days
            }
            
        except Exception as e:
            logger.error(f"Error analyzing outcome trends: {e}")
            return {}
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()


class WorkflowAutomation:
    """Automated workflow management for case management"""
    
    def __init__(self, db_path: str = "social_services.db"):
        self.db_path = db_path
        self.connection = None
    
    def connect(self):
        """Connect to database"""
        if not self.connection:
            # Use check_same_thread=False for Flask threading compatibility
            self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
    
    def create_automated_follow_up_tasks(self) -> List[str]:
        """Create automated follow-up tasks based on referral status"""
        self.connect()
        
        try:
            from services.case_management import CaseManagementTask, CaseManagementDatabase
            
            case_mgmt_db = CaseManagementDatabase(self.db_path)
            cursor = self.connection.cursor()
            
            # Find referrals needing follow-up
            cursor.execute("""
                SELECT r.referral_id, r.client_id, r.case_manager_id, r.provider_id,
                       r.referral_date, r.status, r.priority_level,
                       c.first_name, c.last_name, p.name as provider_name
                FROM service_referrals r
                JOIN clients c ON r.client_id = c.client_id
                JOIN service_providers p ON r.provider_id = p.provider_id
                WHERE r.status = 'Pending' 
                AND julianday('now') - julianday(r.referral_date) >= 3
                AND NOT EXISTS (
                    SELECT 1 FROM case_management_tasks t 
                    WHERE t.referral_id = r.referral_id 
                    AND t.task_type = 'Follow-up'
                    AND t.status != 'Completed'
                )
            """)
            
            pending_referrals = [dict(row) for row in cursor.fetchall()]
            created_tasks = []
            
            for referral in pending_referrals:
                task = CaseManagementTask(
                    case_manager_id=referral['case_manager_id'],
                    client_id=referral['client_id'],
                    referral_id=referral['referral_id'],
                    task_type='Follow-up',
                    title=f'Follow up on referral to {referral["provider_name"]}',
                    description=f'Check status of referral for {referral["first_name"]} {referral["last_name"]}',
                    priority=referral['priority_level'],
                    due_date=(datetime.now() + timedelta(days=1)).isoformat(),
                    is_automated=True,
                    created_by='system'
                )
                
                case_mgmt_db.save_task(task)
                created_tasks.append(task.task_id)
            
            return created_tasks
            
        except Exception as e:
            logger.error(f"Error creating automated follow-up tasks: {e}")
            return []
    
    def check_and_escalate_overdue_referrals(self) -> List[str]:
        """Check for overdue referrals and escalate"""
        self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Find overdue referrals
            cursor.execute("""
                SELECT r.referral_id, r.client_id, r.case_manager_id, r.provider_id,
                       r.referral_date, r.status, r.priority_level,
                       c.first_name, c.last_name, p.name as provider_name
                FROM service_referrals r
                JOIN clients c ON r.client_id = c.client_id
                JOIN service_providers p ON r.provider_id = p.provider_id
                WHERE r.status = 'Pending' 
                AND julianday('now') - julianday(r.referral_date) >= 7
                AND r.priority_level IN ('High', 'Urgent')
            """)
            
            overdue_referrals = [dict(row) for row in cursor.fetchall()]
            escalated_referrals = []
            
            for referral in overdue_referrals:
                # Create escalation task
                from services.case_management import CaseManagementTask, CaseManagementDatabase
                
                case_mgmt_db = CaseManagementDatabase(self.db_path)
                
                task = CaseManagementTask(
                    case_manager_id=referral['case_manager_id'],
                    client_id=referral['client_id'],
                    referral_id=referral['referral_id'],
                    task_type='Escalation',
                    title=f'ESCALATION: Overdue referral to {referral["provider_name"]}',
                    description=f'Referral for {referral["first_name"]} {referral["last_name"]} is overdue - requires immediate attention',
                    priority='Urgent',
                    due_date=datetime.now().isoformat(),
                    is_automated=True,
                    created_by='system'
                )
                
                case_mgmt_db.save_task(task)
                escalated_referrals.append(referral['referral_id'])
            
            return escalated_referrals
            
        except Exception as e:
            logger.error(f"Error escalating overdue referrals: {e}")
            return []
    
    def generate_weekly_summary_tasks(self) -> List[str]:
        """Generate weekly summary tasks for case managers"""
        self.connect()
        
        try:
            cursor = self.connection.cursor()
            
            # Get active case managers
            cursor.execute("""
                SELECT DISTINCT case_manager_id
                FROM clients
                WHERE is_active = 1
            """)
            
            case_managers = [row[0] for row in cursor.fetchall()]
            summary_tasks = []
            
            for case_manager_id in case_managers:
                from services.case_management import CaseManagementTask, CaseManagementDatabase
                
                case_mgmt_db = CaseManagementDatabase(self.db_path)
                
                task = CaseManagementTask(
                    case_manager_id=case_manager_id,
                    task_type='Documentation',
                    title='Weekly Caseload Summary',
                    description='Review and document weekly caseload activities and outcomes',
                    priority='Medium',
                    due_date=(datetime.now() + timedelta(days=7)).isoformat(),
                    is_automated=True,
                    recurring_interval='Weekly',
                    created_by='system'
                )
                
                case_mgmt_db.save_task(task)
                summary_tasks.append(task.task_id)
            
            return summary_tasks
            
        except Exception as e:
            logger.error(f"Error generating weekly summary tasks: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()