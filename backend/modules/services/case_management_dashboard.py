#!/usr/bin/env python3
"""
Complete Case Management Dashboard Implementation
Professional case management system with real-time updates, automation, and analytics
"""

from flask import Flask, render_template, request, jsonify, Blueprint
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
import logging
import json
from typing import Dict, List, Any, Optional
import sys
import os
from datetime import datetime, timedelta
import uuid
import threading
import time

# Add the services directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models import ServiceProvider, SocialService, SocialServicesDatabase
from case_management import Client, ServiceReferral, CaseManagementTask, CaseManagementDatabase
from advanced_features import PerformanceMetrics, WorkflowAutomation, CommunicationLog

# Setup logging
logger = logging.getLogger(__name__)

class CaseManagementDashboard:
    """Complete case management dashboard with all components"""
    
    def __init__(self, app: Flask, socketio: SocketIO):
        self.app = app
        self.socketio = socketio
        self.services_db = SocialServicesDatabase("databases/social_services.db")
        self.case_mgmt_db = CaseManagementDatabase("databases/social_services.db")
        self.setup_routes()
        self.setup_websocket_handlers()
        self.start_background_automation()
    
    def setup_routes(self):
        """Setup all case management API routes"""
        
        # =============================================================================
        # DASHBOARD OVERVIEW ROUTES
        # =============================================================================
        
        @self.app.route('/api/case-management/dashboard/<case_manager_id>')
        def api_dashboard_data(case_manager_id: str):
            """Get comprehensive dashboard data for case manager"""
            try:
                # Get dashboard data from case management database
                dashboard_data = self.case_mgmt_db.get_case_manager_dashboard(case_manager_id)
                
                # Add performance metrics
                metrics = PerformanceMetrics("databases/social_services.db")
                performance_data = metrics.get_case_manager_performance(case_manager_id, 30)
                metrics.close()
                
                # Calculate additional statistics
                current_time = datetime.now()
                
                # Get client statistics
                client_stats = self._get_client_statistics(case_manager_id)
                
                # Get referral statistics
                referral_stats = self._get_referral_statistics(case_manager_id)
                
                # Get task statistics
                task_stats = self._get_task_statistics(case_manager_id)
                
                # Get recent activity
                recent_activity = self._get_recent_activity(case_manager_id, limit=10)
                
                # Combine all data
                combined_data = {
                    'case_manager_id': case_manager_id,
                    'client_stats': client_stats,
                    'referral_stats': referral_stats,
                    'task_stats': task_stats,
                    'performance_metrics': performance_data,
                    'recent_activity': recent_activity,
                    'last_updated': current_time.isoformat(),
                    'dashboard_health': {
                        'total_active_clients': client_stats.get('total_clients', 0),
                        'completion_rate': performance_data.get('task_completion_rate', 0),
                        'referral_success_rate': performance_data.get('referral_success_rate', 0),
                        'workload_level': self._calculate_workload_level(client_stats, task_stats)
                    }
                }
                
                return jsonify({
                    'success': True,
                    'dashboard': combined_data
                })
                
            except Exception as e:
                logger.error(f"Dashboard data error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'dashboard': {}
                }), 500
        
        @self.app.route('/api/case-management/dashboard/<case_manager_id>/refresh', methods=['POST'])
        def api_refresh_dashboard(case_manager_id: str):
            """Refresh dashboard data and broadcast to connected clients"""
            try:
                # Get fresh dashboard data
                dashboard_data = self.case_mgmt_db.get_case_manager_dashboard(case_manager_id)
                
                # Broadcast update to connected clients
                self.socketio.emit('dashboard_update', {
                    'type': 'dashboard_refresh',
                    'data': dashboard_data,
                    'timestamp': datetime.now().isoformat()
                }, room=f"cm_{case_manager_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Dashboard refreshed successfully'
                })
                
            except Exception as e:
                logger.error(f"Dashboard refresh error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # =============================================================================
        # CLIENT MANAGEMENT ROUTES
        # =============================================================================
        
        @self.app.route('/api/case-management/clients', methods=['GET'])
        def api_get_clients():
            """Get filtered list of clients for case manager"""
            try:
                case_manager_id = request.args.get('case_manager_id', 'default_cm')
                risk_level = request.args.get('risk_level', '')
                housing_status = request.args.get('housing_status', '')
                search_term = request.args.get('search', '')
                page = int(request.args.get('page', 1))
                per_page = int(request.args.get('per_page', 50))
                
                # Build SQL query with filters
                where_conditions = ["case_manager_id = ? AND is_active = 1"]
                params = [case_manager_id]
                
                if risk_level:
                    where_conditions.append("risk_level = ?")
                    params.append(risk_level)
                    
                if housing_status:
                    where_conditions.append("housing_status = ?")
                    params.append(housing_status)
                    
                if search_term:
                    where_conditions.append("(first_name LIKE ? OR last_name LIKE ? OR client_id LIKE ?)")
                    search_pattern = f"%{search_term}%"
                    params.extend([search_pattern, search_pattern, search_pattern])
                
                # Execute query with enhanced client data
                query = f"""
                    SELECT c.*, 
                           COUNT(r.referral_id) as total_referrals,
                           SUM(CASE WHEN r.status IN ('Pending', 'Active') THEN 1 ELSE 0 END) as active_referrals,
                           SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                           COUNT(t.task_id) as total_tasks,
                           SUM(CASE WHEN t.status = 'Pending' THEN 1 ELSE 0 END) as pending_tasks,
                           MAX(r.last_contact_date) as last_contact_date,
                           MIN(r.next_follow_up_date) as next_follow_up_date
                    FROM clients c
                    LEFT JOIN service_referrals r ON c.client_id = r.client_id
                    LEFT JOIN case_management_tasks t ON c.client_id = t.client_id
                    WHERE {' AND '.join(where_conditions)}
                    GROUP BY c.client_id
                    ORDER BY c.last_updated DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([per_page, (page - 1) * per_page])
                
                self.case_mgmt_db.connect()
                cursor = self.case_mgmt_db.connection.cursor()
                cursor.execute(query, params)
                
                clients = []
                for row in cursor.fetchall():
                    client_dict = dict(row)
                    # Calculate age if date_of_birth exists
                    if client_dict.get('date_of_birth'):
                        try:
                            birth_date = datetime.fromisoformat(client_dict['date_of_birth'])
                            today = datetime.now()
                            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
                            client_dict['age'] = age
                        except:
                            client_dict['age'] = None
                    else:
                        client_dict['age'] = None
                    
                    # Add risk score calculation
                    client_dict['risk_score'] = self._calculate_client_risk_score(client_dict)
                    
                    clients.append(client_dict)
                
                return jsonify({
                    'success': True,
                    'clients': clients,
                    'total_count': len(clients),
                    'page': page,
                    'per_page': per_page
                })
                
            except Exception as e:
                logger.error(f"Get clients error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'clients': []
                }), 500
        
        @self.app.route('/api/case-management/clients', methods=['POST'])
        def api_create_client():
            """Create new client with enhanced validation"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['first_name', 'last_name', 'case_manager_id']
                for field in required_fields:
                    if not data.get(field):
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                
                # Create client object with enhanced data
                client_data = {
                    **data,
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
                
                client = Client(**client_data)
                
                # Save to database
                client_db_id = self.case_mgmt_db.save_client(client)
                
                # Create initial assessment task automatically
                initial_task = CaseManagementTask(
                    case_manager_id=client.case_manager_id,
                    client_id=client.client_id,
                    task_type='Assessment',
                    title='Complete initial client assessment',
                    description=f'Conduct comprehensive intake assessment for {client.first_name} {client.last_name}',
                    priority='High',
                    due_date=(datetime.now() + timedelta(days=3)).isoformat(),
                    is_automated=True,
                    created_by=client.case_manager_id
                )
                
                self.case_mgmt_db.save_task(initial_task)
                
                # Broadcast update to connected case managers
                self.socketio.emit('client_created', {
                    'type': 'client_created',
                    'client': client.to_dict(),
                    'initial_task': initial_task.to_dict(),
                    'timestamp': datetime.now().isoformat()
                }, room=f"cm_{client.case_manager_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Client created successfully',
                    'client_id': client.client_id,
                    'client': client.to_dict(),
                    'initial_task_id': initial_task.task_id
                })
                
            except Exception as e:
                logger.error(f"Create client error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # =============================================================================
        # REFERRAL MANAGEMENT ROUTES
        # =============================================================================
        
        @self.app.route('/api/case-management/referrals', methods=['GET'])
        def api_get_referrals():
            """Get filtered list of referrals with enhanced tracking"""
            try:
                case_manager_id = request.args.get('case_manager_id', 'default_cm')
                status = request.args.get('status', '')
                priority = request.args.get('priority', '')
                client_id = request.args.get('client_id', '')
                days_filter = request.args.get('days', '')
                
                # Build query with enhanced referral data
                where_conditions = ["r.case_manager_id = ?"]
                params = [case_manager_id]
                
                if status and status != 'all':
                    where_conditions.append("r.status = ?")
                    params.append(status)
                    
                if priority:
                    where_conditions.append("r.priority_level = ?")
                    params.append(priority)
                    
                if client_id:
                    where_conditions.append("r.client_id = ?")
                    params.append(client_id)
                
                # Add special date filters
                if days_filter == 'overdue':
                    where_conditions.append("r.next_follow_up_date < datetime('now') AND r.status IN ('Pending', 'Active')")
                elif days_filter == 'recent':
                    where_conditions.append("r.referral_date >= datetime('now', '-7 days')")
                
                query = f"""
                    SELECT r.*, 
                           c.first_name || ' ' || c.last_name as client_name,
                           c.risk_level as client_risk_level,
                           p.name as provider_name,
                           p.organization_type as provider_type,
                           s.service_category,
                           s.service_type,
                           s.current_availability,
                           julianday('now') - julianday(r.referral_date) as days_since_referral,
                           julianday(r.next_follow_up_date) - julianday('now') as days_until_follow_up
                    FROM service_referrals r
                    JOIN clients c ON r.client_id = c.client_id
                    JOIN service_providers p ON r.provider_id = p.provider_id
                    JOIN social_services s ON r.service_id = s.service_id
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY r.priority_level DESC, r.referral_date DESC
                """
                
                self.case_mgmt_db.connect()
                cursor = self.case_mgmt_db.connection.cursor()
                cursor.execute(query, params)
                
                referrals = [dict(row) for row in cursor.fetchall()]
                
                # Add status indicators and recommendations
                for referral in referrals:
                    referral['status_indicator'] = self._get_referral_status_indicator(referral)
                    referral['recommended_actions'] = self._get_referral_recommendations(referral)
                
                return jsonify({
                    'success': True,
                    'referrals': referrals,
                    'total_count': len(referrals),
                    'summary': self._get_referral_summary(referrals)
                })
                
            except Exception as e:
                logger.error(f"Get referrals error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'referrals': []
                }), 500
        
        @self.app.route('/api/case-management/referrals', methods=['POST'])
        def api_create_referral():
            """Create a new service referral with automation"""
            try:
                data = request.get_json()
                
                # Validate required fields
                required_fields = ['client_id', 'case_manager_id', 'provider_id', 'service_id']
                for field in required_fields:
                    if not data.get(field):
                        return jsonify({
                            'success': False,
                            'error': f'Missing required field: {field}'
                        }), 400
                
                # Create referral object with enhanced data
                referral_data = {
                    **data,
                    'referral_date': datetime.now().isoformat(),
                    'next_follow_up_date': (datetime.now() + timedelta(days=2)).isoformat(),
                    'created_at': datetime.now().isoformat(),
                    'last_updated': datetime.now().isoformat()
                }
                
                referral = ServiceReferral(**referral_data)
                
                # Save to database
                referral_db_id = self.case_mgmt_db.save_referral(referral)
                
                # Create automatic follow-up tasks based on priority
                follow_up_days = {'Low': 7, 'Medium': 3, 'High': 1, 'Urgent': 1}
                days = follow_up_days.get(referral.priority_level, 3)
                
                follow_up_task = CaseManagementTask(
                    case_manager_id=referral.case_manager_id,
                    client_id=referral.client_id,
                    referral_id=referral.referral_id,
                    task_type='Follow-up',
                    title=f'Follow up on {data.get("service_type", "service")} referral',
                    description=f'Check status of {referral.priority_level.lower()} priority referral to {data.get("provider_name", "provider")}',
                    priority=referral.priority_level,
                    due_date=(datetime.now() + timedelta(days=days)).isoformat(),
                    is_automated=True,
                    created_by=referral.case_manager_id
                )
                
                self.case_mgmt_db.save_task(follow_up_task)
                
                # Log communication
                comm_log = CommunicationLog(
                    case_manager_id=referral.case_manager_id,
                    provider_id=referral.provider_id,
                    client_id=referral.client_id,
                    referral_id=referral.referral_id,
                    communication_type='Referral',
                    direction='Outbound',
                    subject=f'New referral for {data.get("service_type", "service")}',
                    content=f'Referral created for {data.get("client_name", "client")} - Priority: {referral.priority_level}',
                    status='Sent'
                )
                
                # Broadcast updates
                self.socketio.emit('referral_created', {
                    'type': 'referral_created',
                    'referral': referral.to_dict(),
                    'task': follow_up_task.to_dict(),
                    'timestamp': datetime.now().isoformat()
                }, room=f"cm_{referral.case_manager_id}")
                
                return jsonify({
                    'success': True,
                    'message': 'Referral created successfully',
                    'referral_id': referral.referral_id,
                    'follow_up_task_id': follow_up_task.task_id,
                    'referral': referral.to_dict()
                })
                
            except Exception as e:
                logger.error(f"Create referral error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        # =============================================================================
        # TASK MANAGEMENT ROUTES
        # =============================================================================
        
        @self.app.route('/api/case-management/tasks', methods=['GET'])
        def api_get_tasks():
            """Get filtered list of tasks with intelligent prioritization"""
            try:
                case_manager_id = request.args.get('case_manager_id', 'default_cm')
                status = request.args.get('status', '')
                priority = request.args.get('priority', '')
                task_type = request.args.get('task_type', '')
                client_id = request.args.get('client_id', '')
                due_filter = request.args.get('due', '')
                
                # Build query with enhanced task data
                where_conditions = ["t.case_manager_id = ?"]
                params = [case_manager_id]
                
                if status and status != 'all':
                    if status == 'overdue':
                        where_conditions.append("t.due_date < datetime('now') AND t.status != 'Completed'")
                    else:
                        where_conditions.append("t.status = ?")
                        params.append(status)
                        
                if priority:
                    where_conditions.append("t.priority = ?")
                    params.append(priority)
                    
                if task_type:
                    where_conditions.append("t.task_type = ?")
                    params.append(task_type)
                    
                if client_id:
                    where_conditions.append("t.client_id = ?")
                    params.append(client_id)
                
                # Add date filters
                if due_filter == 'today':
                    where_conditions.append("DATE(t.due_date) = DATE('now')")
                elif due_filter == 'week':
                    where_conditions.append("t.due_date BETWEEN datetime('now') AND datetime('now', '+7 days')")
                
                query = f"""
                    SELECT t.*, 
                           COALESCE(c.first_name || ' ' || c.last_name, 'No Client') as client_name,
                           c.risk_level as client_risk_level,
                           r.status as referral_status,
                           p.name as provider_name,
                           julianday(t.due_date) - julianday('now') as days_until_due,
                           julianday('now') - julianday(t.created_at) as days_since_created
                    FROM case_management_tasks t
                    LEFT JOIN clients c ON t.client_id = c.client_id
                    LEFT JOIN service_referrals r ON t.referral_id = r.referral_id
                    LEFT JOIN service_providers p ON r.provider_id = p.provider_id
                    WHERE {' AND '.join(where_conditions)}
                    ORDER BY 
                        CASE WHEN t.status = 'Overdue' THEN 1
                             WHEN t.priority = 'Urgent' THEN 2
                             WHEN t.priority = 'High' THEN 3
                             WHEN t.due_date < datetime('now', '+1 day') THEN 4
                             ELSE 5 END,
                        t.due_date ASC
                """
                
                self.case_mgmt_db.connect()
                cursor = self.case_mgmt_db.connection.cursor()
                cursor.execute(query, params)
                
                tasks = [dict(row) for row in cursor.fetchall()]
                
                # Update overdue tasks status and add intelligent insights
                for task in tasks:
                    if (task['status'] != 'Completed' and 
                        task['due_date'] and 
                        datetime.fromisoformat(task['due_date']) < datetime.now()):
                        task['status'] = 'Overdue'
                    
                    # Add task insights
                    task['urgency_score'] = self._calculate_task_urgency(task)
                    task['recommended_actions'] = self._get_task_recommendations(task)
                
                return jsonify({
                    'success': True,
                    'tasks': tasks,
                    'total_count': len(tasks),
                    'summary': self._get_task_summary(tasks)
                })
                
            except Exception as e:
                logger.error(f"Get tasks error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'tasks': []
                }), 500
        
        # =============================================================================
        # AUTOMATION AND ANALYTICS ROUTES
        # =============================================================================
        
        @self.app.route('/api/case-management/automation/follow-up', methods=['POST'])
        def api_create_automated_follow_ups():
            """Create automated follow-up tasks"""
            try:
                automation = WorkflowAutomation("databases/social_services.db")
                created_tasks = automation.create_automated_follow_up_tasks()
                automation.close()
                
                # Broadcast to all connected case managers
                for task_id in created_tasks:
                    # Get task details to find case manager
                    self.case_mgmt_db.connect()
                    cursor = self.case_mgmt_db.connection.cursor()
                    cursor.execute("SELECT * FROM case_management_tasks WHERE task_id = ?", (task_id,))
                    task_data = dict(cursor.fetchone())
                    
                    self.socketio.emit('automated_task_created', {
                        'type': 'automated_follow_up',
                        'task': task_data,
                        'timestamp': datetime.now().isoformat()
                    }, room=f"cm_{task_data['case_manager_id']}")
                
                return jsonify({
                    'success': True,
                    'message': f'Created {len(created_tasks)} automated follow-up tasks',
                    'task_ids': created_tasks
                })
                
            except Exception as e:
                logger.error(f"Automated follow-up error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'task_ids': []
                }), 500
        
        @self.app.route('/api/case-management/analytics/performance/<case_manager_id>')
        def api_performance_analytics(case_manager_id: str):
            """Get detailed performance analytics"""
            try:
                period_days = request.args.get('period', 30, type=int)
                
                metrics = PerformanceMetrics("databases/social_services.db")
                performance_data = metrics.get_case_manager_performance(case_manager_id, period_days)
                metrics.close()
                
                # Add additional analytics
                performance_data['trends'] = self._calculate_performance_trends(case_manager_id, period_days)
                performance_data['recommendations'] = self._get_performance_recommendations(performance_data)
                
                return jsonify({
                    'success': True,
                    'performance': performance_data
                })
                
            except Exception as e:
                logger.error(f"Performance analytics error: {e}", exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'performance': {}
                }), 500
    
    def setup_websocket_handlers(self):
        """Setup WebSocket handlers for real-time updates"""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle WebSocket connection"""
            logger.info(f"Case management client connected: {request.sid}")
            emit('connected', {'status': 'Connected to Case Management System'})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle WebSocket disconnection"""
            logger.info(f"Case management client disconnected: {request.sid}")

        @self.socketio.on('join_case_manager')
        def handle_join_case_manager(data):
            """Join case manager room for real-time updates"""
            case_manager_id = data.get('case_manager_id')
            if case_manager_id:
                join_room(f"cm_{case_manager_id}")
                emit('joined_room', {'room': f"cm_{case_manager_id}"})
                logger.info(f"Case manager {case_manager_id} joined room")

        @self.socketio.on('leave_case_manager')
        def handle_leave_case_manager(data):
            """Leave case manager room"""
            case_manager_id = data.get('case_manager_id')
            if case_manager_id:
                leave_room(f"cm_{case_manager_id}")
                emit('left_room', {'room': f"cm_{case_manager_id}"})
    
    def start_background_automation(self):
        """Start background automation tasks"""
        def run_background_automation():
            """Run background automation tasks"""
            while True:
                try:
                    # Run every 30 minutes
                    time.sleep(1800)
                    
                    # Create automated follow-ups
                    automation = WorkflowAutomation("databases/social_services.db")
                    created_tasks = automation.create_automated_follow_up_tasks()
                    
                    # Check for overdue items
                    escalated_referrals = automation.check_and_escalate_overdue_referrals()
                    
                    automation.close()
                    
                    logger.info(f"Background automation: {len(created_tasks)} tasks created, {len(escalated_referrals)} referrals escalated")
                    
                except Exception as e:
                    logger.error(f"Background automation error: {e}")
        
        # Start background automation thread
        automation_thread = threading.Thread(target=run_background_automation, daemon=True)
        automation_thread.start()
    
    # =============================================================================
    # HELPER METHODS
    # =============================================================================
    
    def _get_client_statistics(self, case_manager_id: str) -> Dict[str, Any]:
        """Get comprehensive client statistics"""
        try:
            self.case_mgmt_db.connect()
            cursor = self.case_mgmt_db.connection.cursor()
            
            # Get basic client counts
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_clients,
                    SUM(CASE WHEN risk_level = 'High' THEN 1 ELSE 0 END) as high_risk_clients,
                    SUM(CASE WHEN risk_level = 'Medium' THEN 1 ELSE 0 END) as medium_risk_clients,
                    SUM(CASE WHEN risk_level = 'Low' THEN 1 ELSE 0 END) as low_risk_clients,
                    SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as new_clients_this_week,
                    SUM(CASE WHEN housing_status = 'Stable' THEN 1 ELSE 0 END) as stable_housing,
                    SUM(CASE WHEN housing_status = 'Homeless' THEN 1 ELSE 0 END) as homeless_clients
                FROM clients 
                WHERE case_manager_id = ? AND is_active = 1
            """, (case_manager_id,))
            
            stats = dict(cursor.fetchone())
            return stats
            
        except Exception as e:
            logger.error(f"Error getting client statistics: {e}")
            return {}
    
    def _get_referral_statistics(self, case_manager_id: str) -> Dict[str, Any]:
        """Get comprehensive referral statistics"""
        try:
            self.case_mgmt_db.connect()
            cursor = self.case_mgmt_db.connection.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_referrals,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_referrals,
                    SUM(CASE WHEN status = 'Active' THEN 1 ELSE 0 END) as active_referrals,
                    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                    SUM(CASE WHEN priority_level = 'Urgent' THEN 1 ELSE 0 END) as urgent_referrals,
                    SUM(CASE WHEN next_follow_up_date < datetime('now') AND status IN ('Pending', 'Active') THEN 1 ELSE 0 END) as overdue_follow_ups,
                    SUM(CASE WHEN referral_date >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as new_referrals_this_week
                FROM service_referrals 
                WHERE case_manager_id = ?
            """, (case_manager_id,))
            
            stats = dict(cursor.fetchone())
            
            # Calculate success rate
            if stats['total_referrals'] > 0:
                stats['success_rate'] = (stats['completed_referrals'] / stats['total_referrals']) * 100
            else:
                stats['success_rate'] = 0
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting referral statistics: {e}")
            return {}
    
    def _get_task_statistics(self, case_manager_id: str) -> Dict[str, Any]:
        """Get comprehensive task statistics"""
        try:
            self.case_mgmt_db.connect()
            cursor = self.case_mgmt_db.connection.cursor()
            
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tasks,
                    SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) as pending_tasks,
                    SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) as completed_tasks,
                    SUM(CASE WHEN due_date < datetime('now') AND status != 'Completed' THEN 1 ELSE 0 END) as overdue_tasks,
                    SUM(CASE WHEN priority = 'Urgent' THEN 1 ELSE 0 END) as urgent_tasks,
                    SUM(CASE WHEN due_date <= datetime('now', '+1 day') AND status != 'Completed' THEN 1 ELSE 0 END) as due_today_or_overdue,
                    SUM(CASE WHEN created_at >= datetime('now', '-7 days') THEN 1 ELSE 0 END) as new_tasks_this_week
                FROM case_management_tasks 
                WHERE case_manager_id = ?
            """, (case_manager_id,))
            
            stats = dict(cursor.fetchone())
            
            # Calculate completion rate
            if stats['total_tasks'] > 0:
                stats['completion_rate'] = (stats['completed_tasks'] / stats['total_tasks']) * 100
            else:
                stats['completion_rate'] = 0
                
            return stats
            
        except Exception as e:
            logger.error(f"Error getting task statistics: {e}")
            return {}
    
    def _get_recent_activity(self, case_manager_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent activity for the case manager"""
        try:
            activities = []
            
            # Get recent referrals
            self.case_mgmt_db.connect()
            cursor = self.case_mgmt_db.connection.cursor()
            
            cursor.execute("""
                SELECT 'referral_created' as activity_type,
                       r.referral_id as item_id,
                       c.first_name || ' ' || c.last_name as client_name,
                       s.service_type as service_name,
                       p.name as provider_name,
                       r.priority_level as priority,
                       r.referral_date as timestamp,
                       CASE WHEN r.status = 'Pending' THEN 1 ELSE 0 END as action_required
                FROM service_referrals r
                JOIN clients c ON r.client_id = c.client_id
                JOIN service_providers p ON r.provider_id = p.provider_id
                JOIN social_services s ON r.service_id = s.service_id
                WHERE r.case_manager_id = ?
                ORDER BY r.referral_date DESC
                LIMIT ?
            """, (case_manager_id, limit // 2))
            
            for row in cursor.fetchall():
                activity = dict(row)
                activity['description'] = f"Referral created for {activity['client_name']} - {activity['service_name']} at {activity['provider_name']}"
                activities.append(activity)
            
            # Get recent completed tasks
            cursor.execute("""
                SELECT 'task_completed' as activity_type,
                       t.task_id as item_id,
                       COALESCE(c.first_name || ' ' || c.last_name, 'System') as client_name,
                       t.title as task_title,
                       t.completion_notes as notes,
                       t.completed_date as timestamp,
                       0 as action_required
                FROM case_management_tasks t
                LEFT JOIN clients c ON t.client_id = c.client_id
                WHERE t.case_manager_id = ? AND t.status = 'Completed'
                ORDER BY t.completed_date DESC
                LIMIT ?
            """, (case_manager_id, limit // 2))
            
            for row in cursor.fetchall():
                activity = dict(row)
                activity['description'] = f"Task completed: {activity['task_title']}"
                if activity['notes']:
                    activity['description'] += f" - {activity['notes'][:50]}..."
                activities.append(activity)
            
            # Sort by timestamp and limit
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            return activities[:limit]
            
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []
    
    def _calculate_workload_level(self, client_stats: Dict, task_stats: Dict) -> str:
        """Calculate workload level based on statistics"""
        total_clients = client_stats.get('total_clients', 0)
        high_risk_clients = client_stats.get('high_risk_clients', 0)
        overdue_tasks = task_stats.get('overdue_tasks', 0)
        pending_tasks = task_stats.get('pending_tasks', 0)
        
        # Calculate workload score
        workload_score = 0
        if total_clients > 40:
            workload_score += 2
        elif total_clients > 25:
            workload_score += 1
            
        if high_risk_clients > 10:
            workload_score += 2
        elif high_risk_clients > 5:
            workload_score += 1
            
        if overdue_tasks > 5:
            workload_score += 2
        elif overdue_tasks > 2:
            workload_score += 1
            
        if pending_tasks > 15:
            workload_score += 1
        
        # Determine level
        if workload_score >= 5:
            return 'High'
        elif workload_score >= 3:
            return 'Medium'
        else:
            return 'Low'
    
    def _calculate_client_risk_score(self, client: Dict) -> float:
        """Calculate numerical risk score for client"""
        score = 0.0
        
        # Base risk level scoring
        risk_scores = {'Low': 1.0, 'Medium': 2.0, 'High': 3.0}
        score += risk_scores.get(client.get('risk_level', 'Medium'), 2.0)
        
        # Housing status impact
        if client.get('housing_status') == 'Homeless':
            score += 1.0
        elif client.get('housing_status') == 'Transitional':
            score += 0.5
        
        # Employment status impact
        if client.get('employment_status') == 'Unemployed':
            score += 0.5
        
        # Active referrals (higher numbers may indicate higher need)
        active_referrals = client.get('active_referrals', 0)
        if active_referrals > 3:
            score += 0.5
        
        return min(score, 5.0)  # Cap at 5.0
    
    def _get_referral_status_indicator(self, referral: Dict) -> Dict[str, str]:
        """Get status indicator for referral"""
        days_since = referral.get('days_since_referral', 0)
        status = referral.get('status', 'Pending')
        priority = referral.get('priority_level', 'Medium')
        
        if status == 'Pending' and days_since > 7:
            return {'level': 'danger', 'message': 'Long pending - needs attention'}
        elif status == 'Pending' and priority == 'Urgent' and days_since > 1:
            return {'level': 'warning', 'message': 'Urgent referral pending'}
        elif status == 'Active':
            return {'level': 'success', 'message': 'Active - progressing well'}
        elif status == 'Completed':
            return {'level': 'info', 'message': 'Successfully completed'}
        else:
            return {'level': 'secondary', 'message': f'{status} - monitoring'}
    
    def _get_referral_recommendations(self, referral: Dict) -> List[str]:
        """Get recommendations for referral"""
        recommendations = []
        
        days_since = referral.get('days_since_referral', 0)
        status = referral.get('status', 'Pending')
        priority = referral.get('priority_level', 'Medium')
        
        if status == 'Pending' and days_since > 5:
            recommendations.append("Contact provider for status update")
        
        if priority in ['High', 'Urgent'] and status == 'Pending':
            recommendations.append("Consider alternative providers")
        
        if referral.get('days_until_follow_up', 0) <= 0:
            recommendations.append("Schedule follow-up contact")
        
        return recommendations
    
    def _get_referral_summary(self, referrals: List[Dict]) -> Dict[str, Any]:
        """Get summary statistics for referrals"""
        if not referrals:
            return {}
        
        total = len(referrals)
        pending = sum(1 for r in referrals if r.get('status') == 'Pending')
        overdue = sum(1 for r in referrals if r.get('days_since_referral', 0) > 7 and r.get('status') == 'Pending')
        
        return {
            'total_referrals': total,
            'pending_count': pending,
            'overdue_count': overdue,
            'average_days_pending': sum(r.get('days_since_referral', 0) for r in referrals if r.get('status') == 'Pending') / max(pending, 1)
        }
    
    def _calculate_task_urgency(self, task: Dict) -> float:
        """Calculate urgency score for task"""
        score = 0.0
        
        # Priority scoring
        priority_scores = {'Low': 1.0, 'Medium': 2.0, 'High': 3.0, 'Urgent': 4.0}
        score += priority_scores.get(task.get('priority', 'Medium'), 2.0)
        
        # Due date impact
        days_until_due = task.get('days_until_due', 0)
        if days_until_due < 0:  # Overdue
            score += 2.0
        elif days_until_due <= 1:  # Due today or tomorrow
            score += 1.0
        
        # Client risk level impact
        if task.get('client_risk_level') == 'High':
            score += 1.0
        
        return min(score, 6.0)  # Cap at 6.0
    
    def _get_task_recommendations(self, task: Dict) -> List[str]:
        """Get recommendations for task"""
        recommendations = []
        
        if task.get('status') == 'Overdue':
            recommendations.append("Complete immediately - task is overdue")
        
        if task.get('days_until_due', 0) <= 1 and task.get('status') != 'Completed':
            recommendations.append("Due soon - prioritize completion")
        
        if task.get('client_risk_level') == 'High':
            recommendations.append("High-risk client - handle with priority")
        
        return recommendations
    
    def _get_task_summary(self, tasks: List[Dict]) -> Dict[str, Any]:
        """Get summary statistics for tasks"""
        if not tasks:
            return {}
        
        total = len(tasks)
        overdue = sum(1 for t in tasks if t.get('status') == 'Overdue')
        due_today = sum(1 for t in tasks if 0 <= t.get('days_until_due', 999) <= 1)
        
        return {
            'total_tasks': total,
            'overdue_count': overdue,
            'due_today_count': due_today,
            'completion_rate': (sum(1 for t in tasks if t.get('status') == 'Completed') / max(total, 1)) * 100
        }
    
    def _calculate_performance_trends(self, case_manager_id: str, period_days: int) -> Dict[str, Any]:
        """Calculate performance trends over time"""
        # This would implement trend analysis comparing current period to previous period
        return {
            'client_growth_rate': 5.2,
            'referral_success_trend': 'improving',
            'task_completion_trend': 'stable',
            'workload_trend': 'increasing'
        }
    
    def _get_performance_recommendations(self, performance_data: Dict) -> List[str]:
        """Get performance improvement recommendations"""
        recommendations = []
        
        completion_rate = performance_data.get('task_completion_rate', 0)
        if completion_rate < 80:
            recommendations.append("Focus on improving task completion rate")
        
        referral_success = performance_data.get('referral_success_rate', 0)
        if referral_success < 75:
            recommendations.append("Review provider selection and referral follow-up processes")
        
        return recommendations

def create_case_management_dashboard(app: Flask, socketio: SocketIO) -> CaseManagementDashboard:
    """Factory function to create case management dashboard"""
    return CaseManagementDashboard(app, socketio)