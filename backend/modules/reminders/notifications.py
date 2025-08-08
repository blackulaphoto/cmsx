#!/usr/bin/env python3
"""
Mobile Notification System for Intelligent Case Management
Push notifications, SMS alerts, and email notifications for urgent items
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from .models import ReminderDatabase

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Comprehensive notification service for case management reminders
    """
    
    def __init__(self, reminder_db: ReminderDatabase):
        self.reminder_db = reminder_db
        self.notification_db = self._create_notification_database()
        
        # Notification settings
        self.notification_settings = {
            'push_notifications': True,
            'sms_alerts': True,
            'email_notifications': True,
            'quiet_hours': {'start': '22:00', 'end': '07:00'},
            'max_notifications_per_hour': 5,
            'urgent_override': True
        }
    
    def _create_notification_database(self):
        """Create notification tracking database"""
        if not self.reminder_db.connection:
            self.reminder_db.connect()
        
        notification_tables = [
            """
            CREATE TABLE IF NOT EXISTS notification_preferences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_manager_id TEXT UNIQUE NOT NULL,
                push_enabled INTEGER DEFAULT 1,
                sms_enabled INTEGER DEFAULT 1,
                email_enabled INTEGER DEFAULT 1,
                phone_number TEXT,
                email_address TEXT,
                quiet_hours_start TEXT DEFAULT '22:00',
                quiet_hours_end TEXT DEFAULT '07:00',
                max_hourly_notifications INTEGER DEFAULT 5,
                urgent_override INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notification_id TEXT UNIQUE NOT NULL,
                case_manager_id TEXT NOT NULL,
                client_id TEXT,
                notification_type TEXT NOT NULL,
                channel TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT NOT NULL,
                sent_at TEXT,
                delivered_at TEXT,
                opened_at TEXT,
                status TEXT DEFAULT 'pending',
                retry_count INTEGER DEFAULT 0,
                error_message TEXT,
                created_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS notification_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_manager_id TEXT NOT NULL,
                device_token TEXT NOT NULL,
                device_type TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
            """
        ]
        
        try:
            for table_sql in notification_tables:
                self.reminder_db.connection.execute(table_sql)
            self.reminder_db.connection.commit()
            logger.info("Notification database tables created successfully")
            return self.reminder_db.connection
        except Exception as e:
            logger.error(f"Failed to create notification tables: {e}")
            raise
    
    def register_device(self, case_manager_id: str, device_token: str, device_type: str = 'web') -> bool:
        """Register device for push notifications"""
        try:
            cursor = self.notification_db.cursor()
            
            # Check if device already registered
            cursor.execute("""
                SELECT id FROM notification_subscriptions 
                WHERE case_manager_id = ? AND device_token = ?
            """, (case_manager_id, device_token))
            
            if cursor.fetchone():
                # Update existing registration
                cursor.execute("""
                    UPDATE notification_subscriptions 
                    SET is_active = 1, updated_at = ? 
                    WHERE case_manager_id = ? AND device_token = ?
                """, (datetime.now().isoformat(), case_manager_id, device_token))
            else:
                # Insert new registration
                cursor.execute("""
                    INSERT INTO notification_subscriptions 
                    (case_manager_id, device_token, device_type, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (case_manager_id, device_token, device_type, 
                     datetime.now().isoformat(), datetime.now().isoformat()))
            
            self.notification_db.commit()
            logger.info(f"Device registered for case manager {case_manager_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return False
    
    def update_notification_preferences(self, case_manager_id: str, preferences: Dict[str, Any]) -> bool:
        """Update notification preferences for a case manager"""
        try:
            cursor = self.notification_db.cursor()
            
            # Insert or update preferences
            cursor.execute("""
                INSERT OR REPLACE INTO notification_preferences 
                (case_manager_id, push_enabled, sms_enabled, email_enabled, 
                 phone_number, email_address, quiet_hours_start, quiet_hours_end,
                 max_hourly_notifications, urgent_override, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case_manager_id,
                preferences.get('push_enabled', 1),
                preferences.get('sms_enabled', 1),
                preferences.get('email_enabled', 1),
                preferences.get('phone_number', ''),
                preferences.get('email_address', ''),
                preferences.get('quiet_hours_start', '22:00'),
                preferences.get('quiet_hours_end', '07:00'),
                preferences.get('max_hourly_notifications', 5),
                preferences.get('urgent_override', 1),
                datetime.now().isoformat()
            ))
            
            self.notification_db.commit()
            logger.info(f"Updated notification preferences for {case_manager_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update notification preferences: {e}")
            return False
    
    def send_urgent_alert(self, case_manager_id: str, client_id: str, alert_type: str, 
                         message: str, context: Dict[str, Any] = None) -> bool:
        """Send urgent alert notification"""
        try:
            # Get notification preferences
            preferences = self._get_notification_preferences(case_manager_id)
            
            # Create notification
            notification = {
                'case_manager_id': case_manager_id,
                'client_id': client_id,
                'notification_type': alert_type,
                'title': self._generate_alert_title(alert_type, context),
                'message': message,
                'priority': 'urgent',
                'context': context or {}
            }
            
            # Send via multiple channels
            success = False
            
            # Push notification
            if preferences.get('push_enabled', True):
                success |= self._send_push_notification(notification)
            
            # SMS alert for urgent items
            if preferences.get('sms_enabled', True) and preferences.get('phone_number'):
                success |= self._send_sms_notification(notification, preferences['phone_number'])
            
            # Email notification
            if preferences.get('email_enabled', True) and preferences.get('email_address'):
                success |= self._send_email_notification(notification, preferences['email_address'])
            
            # Log notification
            self._log_notification(notification, 'urgent_alert', success)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send urgent alert: {e}")
            return False
    
    def send_daily_summary(self, case_manager_id: str, summary_data: Dict[str, Any]) -> bool:
        """Send daily summary notification"""
        try:
            preferences = self._get_notification_preferences(case_manager_id)
            
            # Create summary notification
            notification = {
                'case_manager_id': case_manager_id,
                'client_id': None,
                'notification_type': 'daily_summary',
                'title': f"Daily Summary - {summary_data.get('urgent_count', 0)} urgent items",
                'message': self._generate_summary_message(summary_data),
                'priority': 'normal',
                'context': summary_data
            }
            
            # Send via preferred channels
            success = False
            
            # Push notification
            if preferences.get('push_enabled', True):
                success |= self._send_push_notification(notification)
            
            # Email summary (optional)
            if preferences.get('email_enabled', True) and preferences.get('email_address'):
                success |= self._send_email_summary(notification, preferences['email_address'])
            
            # Log notification
            self._log_notification(notification, 'daily_summary', success)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def send_milestone_alert(self, case_manager_id: str, client_id: str, milestone: Dict[str, Any]) -> bool:
        """Send milestone alert notification"""
        try:
            preferences = self._get_notification_preferences(case_manager_id)
            
            # Create milestone notification
            notification = {
                'case_manager_id': case_manager_id,
                'client_id': client_id,
                'notification_type': 'milestone_alert',
                'title': f"Milestone Alert: {milestone.get('milestone', 'Unknown')}",
                'message': f"Client {milestone.get('client_name', 'Unknown')} has reached {milestone.get('milestone', 'a milestone')}. Action required: {milestone.get('action_required', 'Review needed')}",
                'priority': 'high',
                'context': milestone
            }
            
            # Send notifications
            success = False
            
            # Push notification
            if preferences.get('push_enabled', True):
                success |= self._send_push_notification(notification)
            
            # SMS for critical milestones
            if milestone.get('urgency') == 'Critical' and preferences.get('sms_enabled', True):
                success |= self._send_sms_notification(notification, preferences.get('phone_number'))
            
            # Log notification
            self._log_notification(notification, 'milestone_alert', success)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to send milestone alert: {e}")
            return False
    
    def _send_push_notification(self, notification: Dict[str, Any]) -> bool:
        """Send push notification via web push or mobile push"""
        try:
            # Get device tokens for case manager
            case_manager_id = notification['case_manager_id']
            cursor = self.notification_db.cursor()
            
            cursor.execute("""
                SELECT device_token, device_type FROM notification_subscriptions 
                WHERE case_manager_id = ? AND is_active = 1
            """, (case_manager_id,))
            
            devices = cursor.fetchall()
            
            if not devices:
                logger.warning(f"No registered devices for case manager {case_manager_id}")
                return False
            
            # Send to all registered devices
            success_count = 0
            for device in devices:
                device_token, device_type = device
                
                # Mock push notification implementation
                # In production, this would use services like Firebase Cloud Messaging
                push_payload = {
                    'title': notification['title'],
                    'body': notification['message'],
                    'data': {
                        'client_id': notification.get('client_id'),
                        'notification_type': notification['notification_type'],
                        'priority': notification['priority'],
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                # Simulate push notification
                logger.info(f"PUSH NOTIFICATION to {device_type}: {push_payload}")
                success_count += 1
            
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False
    
    def _send_sms_notification(self, notification: Dict[str, Any], phone_number: str) -> bool:
        """Send SMS notification"""
        try:
            # Mock SMS implementation
            # In production, this would use services like Twilio
            sms_message = f"URGENT: {notification['title']} - {notification['message'][:100]}..."
            
            logger.info(f"SMS NOTIFICATION to {phone_number}: {sms_message}")
            
            # Here you would integrate with SMS service
            # Example: twilio_client.messages.create(body=sms_message, to=phone_number, from_=twilio_number)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False
    
    def _send_email_notification(self, notification: Dict[str, Any], email_address: str) -> bool:
        """Send email notification"""
        try:
            # Mock email implementation
            # In production, this would use services like SendGrid or AWS SES
            email_subject = f"Case Management Alert: {notification['title']}"
            email_body = self._generate_email_body(notification)
            
            logger.info(f"EMAIL NOTIFICATION to {email_address}: {email_subject}")
            
            # Here you would integrate with email service
            # Example: sendgrid_client.send(email_subject, email_body, email_address)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_email_summary(self, notification: Dict[str, Any], email_address: str) -> bool:
        """Send detailed email summary"""
        try:
            summary_data = notification.get('context', {})
            
            email_subject = f"Daily Case Management Summary - {datetime.now().strftime('%Y-%m-%d')}"
            email_body = self._generate_summary_email_body(summary_data)
            
            logger.info(f"EMAIL SUMMARY to {email_address}: {email_subject}")
            
            # Here you would send the detailed email summary
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email summary: {e}")
            return False
    
    def _get_notification_preferences(self, case_manager_id: str) -> Dict[str, Any]:
        """Get notification preferences for case manager"""
        try:
            cursor = self.notification_db.cursor()
            cursor.execute("""
                SELECT * FROM notification_preferences WHERE case_manager_id = ?
            """, (case_manager_id,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            else:
                # Return default preferences
                return {
                    'push_enabled': True,
                    'sms_enabled': True,
                    'email_enabled': True,
                    'phone_number': '',
                    'email_address': '',
                    'quiet_hours_start': '22:00',
                    'quiet_hours_end': '07:00',
                    'max_hourly_notifications': 5,
                    'urgent_override': True
                }
                
        except Exception as e:
            logger.error(f"Failed to get notification preferences: {e}")
            return {}
    
    def _generate_alert_title(self, alert_type: str, context: Dict[str, Any]) -> str:
        """Generate appropriate alert title"""
        titles = {
            'urgent_contact': 'Urgent Contact Required',
            'overdue_task': 'Overdue Task Alert',
            'milestone_reached': 'Program Milestone Reached',
            'crisis_alert': 'Client Crisis Alert',
            'discharge_warning': 'Discharge Date Approaching',
            'housing_emergency': 'Housing Emergency'
        }
        
        return titles.get(alert_type, 'Case Management Alert')
    
    def _generate_summary_message(self, summary_data: Dict[str, Any]) -> str:
        """Generate daily summary message"""
        urgent_count = summary_data.get('urgent_count', 0)
        high_priority_count = summary_data.get('high_priority_count', 0)
        total_clients = summary_data.get('total_clients', 0)
        
        if urgent_count > 0:
            return f"Good morning! You have {urgent_count} urgent items and {high_priority_count} high-priority tasks across {total_clients} clients today."
        else:
            return f"Good morning! You have {high_priority_count} high-priority tasks across {total_clients} clients today. No urgent items!"
    
    def _generate_email_body(self, notification: Dict[str, Any]) -> str:
        """Generate email body for notification"""
        return f"""
        <html>
        <body>
            <h2>{notification['title']}</h2>
            <p>{notification['message']}</p>
            <p><strong>Priority:</strong> {notification['priority'].upper()}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            {self._generate_context_html(notification.get('context', {}))}
            
            <p>Please log into your case management system to take action.</p>
            <p>This is an automated message from your Intelligent Case Management System.</p>
        </body>
        </html>
        """
    
    def _generate_summary_email_body(self, summary_data: Dict[str, Any]) -> str:
        """Generate detailed email summary body"""
        return f"""
        <html>
        <body>
            <h2>Daily Case Management Summary</h2>
            <p><strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}</p>
            
            <h3>Summary Statistics</h3>
            <ul>
                <li><strong>Total Clients:</strong> {summary_data.get('total_clients', 0)}</li>
                <li><strong>Urgent Items:</strong> {summary_data.get('urgent_count', 0)}</li>
                <li><strong>High Priority:</strong> {summary_data.get('high_priority_count', 0)}</li>
                <li><strong>Scheduled Tasks:</strong> {summary_data.get('scheduled_count', 0)}</li>
            </ul>
            
            <h3>Today's Focus</h3>
            <p>{summary_data.get('focus_recommendation', 'No specific recommendations')}</p>
            
            <h3>High Risk Clients</h3>
            {self._generate_high_risk_html(summary_data.get('high_risk_clients', []))}
            
            <h3>Milestone Alerts</h3>
            {self._generate_milestone_html(summary_data.get('milestone_alerts', []))}
            
            <p>Please log into your case management system for detailed task management.</p>
            <p>This is an automated summary from your Intelligent Case Management System.</p>
        </body>
        </html>
        """
    
    def _generate_context_html(self, context: Dict[str, Any]) -> str:
        """Generate HTML for notification context"""
        if not context:
            return ""
        
        html = "<h4>Additional Details:</h4><ul>"
        for key, value in context.items():
            if isinstance(value, (str, int, float)):
                html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        html += "</ul>"
        return html
    
    def _generate_high_risk_html(self, high_risk_clients: List[Dict[str, Any]]) -> str:
        """Generate HTML for high risk clients"""
        if not high_risk_clients:
            return "<p>No high-risk clients identified.</p>"
        
        html = "<ul>"
        for client in high_risk_clients:
            html += f"<li><strong>{client.get('client_name', 'Unknown')}:</strong> {', '.join(client.get('risk_factors', []))}</li>"
        html += "</ul>"
        return html
    
    def _generate_milestone_html(self, milestone_alerts: List[Dict[str, Any]]) -> str:
        """Generate HTML for milestone alerts"""
        if not milestone_alerts:
            return "<p>No milestone alerts today.</p>"
        
        html = "<ul>"
        for alert in milestone_alerts:
            html += f"<li><strong>{alert.get('client_name', 'Unknown')}:</strong> {alert.get('milestone', 'Unknown milestone')} - {alert.get('action_required', 'Action required')}</li>"
        html += "</ul>"
        return html
    
    def _log_notification(self, notification: Dict[str, Any], channel: str, success: bool):
        """Log notification attempt"""
        try:
            cursor = self.notification_db.cursor()
            cursor.execute("""
                INSERT INTO notification_log 
                (notification_id, case_manager_id, client_id, notification_type, 
                 channel, title, message, priority, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"notif_{datetime.now().timestamp()}",
                notification['case_manager_id'],
                notification.get('client_id'),
                notification['notification_type'],
                channel,
                notification['title'],
                notification['message'],
                notification['priority'],
                'sent' if success else 'failed',
                datetime.now().isoformat()
            ))
            
            self.notification_db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log notification: {e}")
    
    def get_notification_history(self, case_manager_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get notification history for case manager"""
        try:
            cursor = self.notification_db.cursor()
            cursor.execute("""
                SELECT * FROM notification_log 
                WHERE case_manager_id = ? 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (case_manager_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Failed to get notification history: {e}")
            return []
    
    def get_notification_stats(self, case_manager_id: str) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            cursor = self.notification_db.cursor()
            
            # Total notifications sent
            cursor.execute("""
                SELECT COUNT(*) FROM notification_log 
                WHERE case_manager_id = ?
            """, (case_manager_id,))
            total_sent = cursor.fetchone()[0]
            
            # Successful notifications
            cursor.execute("""
                SELECT COUNT(*) FROM notification_log 
                WHERE case_manager_id = ? AND status = 'sent'
            """, (case_manager_id,))
            successful = cursor.fetchone()[0]
            
            # Notifications by type
            cursor.execute("""
                SELECT notification_type, COUNT(*) 
                FROM notification_log 
                WHERE case_manager_id = ? 
                GROUP BY notification_type
            """, (case_manager_id,))
            by_type = dict(cursor.fetchall())
            
            return {
                'total_sent': total_sent,
                'successful': successful,
                'success_rate': (successful / total_sent * 100) if total_sent > 0 else 0,
                'by_type': by_type
            }
            
        except Exception as e:
            logger.error(f"Failed to get notification stats: {e}")
            return {}

class NotificationScheduler:
    """
    Automated notification scheduler that monitors for urgent conditions
    """
    
    def __init__(self, notification_service: NotificationService):
        self.notification_service = notification_service
    
    def check_urgent_conditions(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Check for urgent conditions that require immediate notification"""
        urgent_conditions = []
        
        try:
            # Mock urgent conditions for demo - in production would check actual data
            mock_urgent_conditions = [
                {
                    'type': 'high_risk_client',
                    'client_id': 'client_001',
                    'client_name': 'John Smith',
                    'message': 'High-risk client John Smith requires immediate attention - 5 days since last contact',
                    'context': {'risk_level': 'High', 'days_since_contact': 5}
                }
            ]
            
            return mock_urgent_conditions
            
        except Exception as e:
            logger.error(f"Failed to check urgent conditions: {e}")
            return []
    
    def send_morning_summary(self, case_manager_id: str) -> bool:
        """Send morning summary notification"""
        try:
            # Mock summary data for demo - in production would get from actual data
            summary_data = {
                'total_clients': 15,
                'urgent_count': 3,
                'high_priority_count': 5,
                'scheduled_count': 7,
                'focus_recommendation': 'Priority: Contact 3 high-risk clients and complete 2 overdue assessments',
                'high_risk_clients': [
                    {'client_name': 'John Smith', 'risk_factors': ['High risk client', 'No recent contact']}
                ],
                'milestone_alerts': []
            }
            
            return self.notification_service.send_daily_summary(case_manager_id, summary_data)
            
        except Exception as e:
            logger.error(f"Failed to send morning summary: {e}")
            return False
    
    def process_urgent_alerts(self, case_manager_id: str) -> int:
        """Process and send urgent alerts"""
        urgent_conditions = self.check_urgent_conditions(case_manager_id)
        alerts_sent = 0
        
        for condition in urgent_conditions:
            try:
                success = self.notification_service.send_urgent_alert(
                    case_manager_id=case_manager_id,
                    client_id=condition['client_id'],
                    alert_type=condition['type'],
                    message=condition['message'],
                    context=condition.get('context', {})
                )
                
                if success:
                    alerts_sent += 1
                    
            except Exception as e:
                logger.error(f"Failed to send urgent alert: {e}")
        
        return alerts_sent