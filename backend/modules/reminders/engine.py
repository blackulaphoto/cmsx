#!/usr/bin/env python3
"""
Intelligent Case Management Reminder Engine
Core AI-powered logic for smart client contact tracking and deadline management
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from .models import ReminderDatabase, ClientContact, ReminderRule, ProgramMilestone, ActiveReminder

logger = logging.getLogger(__name__)

class IntelligentReminderEngine:
    """
    Core AI-powered reminder engine that calculates:
    - When clients need contact based on risk level
    - Program milestone triggers
    - Deadline urgency scoring
    - Automatic priority adjustment
    """
    
    def __init__(self, reminder_db: ReminderDatabase = None):
        self.reminder_db = reminder_db or ReminderDatabase('databases/reminders.db')
        self.current_date = datetime.now()
        
        # Risk-based contact frequency (days)
        self.contact_frequency = {
            'High': 3,      # High risk: every 2-3 days
            'Medium': 7,    # Medium risk: every 5-7 days  
            'Low': 14       # Low risk: every 10-14 days
        }
        
        # Priority scoring weights
        self.priority_weights = {
            'days_overdue': 10,
            'risk_level': 5,
            'crisis_indicators': 20,
            'program_milestone': 15,
            'deadline_proximity': 25
        }
    
    def calculate_contact_urgency(self, client_id: str, case_manager_id: str) -> Dict[str, Any]:
        """
        Calculate when a client needs contact based on:
        - Risk level
        - Days since last contact
        - Recent crisis indicators
        - Program timeline
        """
        try:
            # Get client data from database
            client_data = self.reminder_db.get_client_data(client_id)
            if not client_data:
                return {'error': 'Client not found'}
            
            # Get last contact info
            last_contact = self.reminder_db.get_last_contact(client_id, case_manager_id)
            days_since_contact = 0
            
            if last_contact:
                last_contact_date = datetime.fromisoformat(last_contact['contact_date'])
                days_since_contact = (self.current_date - last_contact_date).days
            else:
                days_since_contact = 999  # No contact recorded
            
            # Calculate urgency score
            urgency_score = 0
            risk_level = client_data.get('risk_level', 'Medium')
            
            # Days overdue calculation
            expected_frequency = self.contact_frequency.get(risk_level, 7)
            days_overdue = max(0, days_since_contact - expected_frequency)
            urgency_score += days_overdue * self.priority_weights['days_overdue']
            
            # Risk level scoring
            risk_scores = {'High': 20, 'Medium': 10, 'Low': 5}
            urgency_score += risk_scores.get(risk_level, 10)
            
            # Crisis indicators
            if client_data.get('crisis_level') == 'Active':
                urgency_score += 100
            elif client_data.get('crisis_level') == 'Recent':
                urgency_score += 50
            
            # Program milestone proximity
            days_until_discharge = client_data.get('days_until_discharge', 999)
            if days_until_discharge <= 7:
                urgency_score += 50
            elif days_until_discharge <= 14:
                urgency_score += 25
            
            # Determine urgency level
            if urgency_score >= 100:
                urgency_level = 'URGENT'
            elif urgency_score >= 70:
                urgency_level = 'HIGH'
            elif urgency_score >= 40:
                urgency_level = 'MEDIUM'
            else:
                urgency_level = 'SCHEDULED'
            
            return {
                'client_id': client_id,
                'urgency_level': urgency_level,
                'urgency_score': urgency_score,
                'days_since_contact': days_since_contact,
                'days_overdue': days_overdue,
                'expected_frequency': expected_frequency,
                'risk_level': risk_level,
                'recommended_action': self._get_recommended_action(urgency_level, days_overdue)
            }
            
        except Exception as e:
            logger.error(f"Error calculating contact urgency: {e}")
            return {'error': str(e)}
    
    def _get_recommended_action(self, urgency_level: str, days_overdue: int) -> str:
        """Get recommended action based on urgency"""
        if urgency_level == 'URGENT':
            return 'Immediate contact required'
        elif urgency_level == 'HIGH':
            return 'Contact within 24 hours'
        elif urgency_level == 'MEDIUM':
            return 'Schedule contact this week'
        else:
            return 'Contact as scheduled'
    
    def generate_daily_reminders(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Generate daily reminder list for case manager"""
        try:
            # Get all clients for case manager
            clients = self.reminder_db.get_clients_for_case_manager(case_manager_id)
            reminders = []
            
            for client in clients:
                urgency_data = self.calculate_contact_urgency(client['client_id'], case_manager_id)
                
                if urgency_data.get('urgency_level') in ['URGENT', 'HIGH']:
                    reminders.append({
                        'client_id': client['client_id'],
                        'client_name': client.get('client_name', 'Unknown'),
                        'urgency_level': urgency_data['urgency_level'],
                        'message': f"Contact {client.get('client_name', 'client')} - {urgency_data['days_since_contact']} days since last contact",
                        'action': urgency_data['recommended_action'],
                        'priority_score': urgency_data['urgency_score']
                    })
            
            # Sort by priority score
            reminders.sort(key=lambda x: x['priority_score'], reverse=True)
            return reminders
            
        except Exception as e:
            logger.error(f"Error generating daily reminders: {e}")
            return []
    
    def generate_morning_dashboard(self, case_manager_id: str) -> Dict[str, Any]:
        """Generate morning dashboard with urgent and today items"""
        try:
            # Get all clients for case manager
            clients = self.reminder_db.get_clients_for_case_manager(case_manager_id)
            
            urgent_items = []
            today_items = []
            
            for client in clients:
                urgency_data = self.calculate_contact_urgency(client['client_id'], case_manager_id)
                
                if urgency_data.get('urgency_level') == 'URGENT':
                    urgent_items.append({
                        'client_id': client['client_id'],
                        'client_name': client.get('client_name', 'Unknown'),
                        'type': 'contact',
                        'action': urgency_data['recommended_action'],
                        'message': f"Contact {client.get('client_name', 'client')} - {urgency_data['days_since_contact']} days since last contact",
                        'days_overdue': urgency_data.get('days_overdue', 0)
                    })
                elif urgency_data.get('urgency_level') == 'HIGH':
                    today_items.append({
                        'client_id': client['client_id'],
                        'client_name': client.get('client_name', 'Unknown'),
                        'type': 'contact',
                        'action': urgency_data['recommended_action'],
                        'message': f"Contact {client.get('client_name', 'client')} - {urgency_data['days_since_contact']} days since last contact"
                    })
            
            return {
                'case_manager_id': case_manager_id,
                'generated_at': self.current_date.isoformat(),
                'urgent_items': urgent_items,
                'today_items': today_items,
                'total_urgent': len(urgent_items),
                'total_today': len(today_items)
            }
            
        except Exception as e:
            logger.error(f"Error generating morning dashboard: {e}")
            return {'error': str(e)}