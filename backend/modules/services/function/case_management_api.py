#!/usr/bin/env python3
"""
Complete Case Management API Implementation
Flask routes, WebSocket handlers, and business logic for professional case management
"""

from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
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
sys.path.append('/app/services')

from services.models import ServiceProvider, SocialService, SocialServicesDatabase
from services.case_management import Client, ServiceReferral, CaseManagementTask, CaseManagementDatabase
from services.advanced_features import PerformanceMetrics, WorkflowAutomation, CommunicationLog

# Initialize Flask app with SocketIO
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize database connections
services_db = SocialServicesDatabase("databases/social_services.db")
case_mgmt_db = CaseManagementDatabase("databases/social_services.db")

logger = logging.getLogger(__name__)

# =============================================================================
# REAL-TIME WEBSOCKET HANDLERS
# =============================================================================

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('connected', {'status': 'Connected to Case Management System'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_case_manager')
def handle_join_case_manager(data):
    """Join case manager room for real-time updates"""
    case_manager_id = data.get('case_manager_id')
    if case_manager_id:
        join_room(f"cm_{case_manager_id}")
        emit('joined_room', {'room': f"cm_{case_manager_id}"})
        logger.info(f"Case manager {case_manager_id} joined room")

@socketio.on('leave_case_manager')
def handle_leave_case_manager(data):
    """Leave case manager room"""
    case_manager_id = data.get('case_manager_id')
    if case_manager_id:
        leave_room(f"cm_{case_manager_id}")
        emit('left_room', {'room': f"cm_{case_manager_id}"})

# =============================================================================
# DASHBOARD API ENDPOINTS
# =============================================================================

@app.route('/api/dashboard/<case_manager_id>')
def api_dashboard_data(case_manager_id: str):
    """Get comprehensive dashboard data for case manager"""
    try:
        # Get dashboard data from case management database
        dashboard_data = case_mgmt_db.get_case_manager_dashboard(case_manager_id)
        
        # Add performance metrics
        metrics = PerformanceMetrics("databases/social_services.db")
        performance_data = metrics.get_case_manager_performance(case_manager_id, 30)
        metrics.close()
        
        # Combine dashboard and performance data
        combined_data = {
            **dashboard_data,
            'performance_metrics': performance_data,
            'last_updated': datetime.now().isoformat()
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

@app.route('/api/dashboard/<case_manager_id>/refresh', methods=['POST'])
def api_refresh_dashboard(case_manager_id: str):
    """Refresh dashboard data and broadcast to connected clients"""
    try:
        # Get fresh dashboard data
        dashboard_data = case_mgmt_db.get_case_manager_dashboard(case_manager_id)
        
        # Broadcast update to connected clients
        socketio.emit('dashboard_update', {
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
# CLIENT MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/clients', methods=['GET'])
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
        
        # Execute query
        query = f"""
            SELECT c.*, 
                   COUNT(r.referral_id) as total_referrals,
                   SUM(CASE WHEN r.status IN ('Pending', 'Active') THEN 1 ELSE 0 END) as active_referrals,
                   SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                   MAX(r.last_contact_date) as last_contact_date
            FROM clients c
            LEFT JOIN service_referrals r ON c.client_id = r.client_id
            WHERE {' AND '.join(where_conditions)}
            GROUP BY c.client_id
            ORDER BY c.last_updated DESC
            LIMIT ? OFFSET ?
        """
        params.extend([per_page, (page - 1) * per_page])
        
        case_mgmt_db.connect()
        cursor = case_mgmt_db.connection.cursor()
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

@app.route('/api/clients', methods=['POST'])
def api_create_client():
    """Create new client"""
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
        
        # Create client object
        client = Client(**data)
        
        # Save to database
        client_db_id = case_mgmt_db.save_client(client)
        
        # Broadcast update to connected case managers
        socketio.emit('client_created', {
            'type': 'client_created',
            'client': client.to_dict(),
            'timestamp': datetime.now().isoformat()
        }, room=f"cm_{client.case_manager_id}")
        
        return jsonify({
            'success': True,
            'message': 'Client created successfully',
            'client_id': client.client_id,
            'client': client.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Create client error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clients/<client_id>', methods=['GET'])
def api_get_client_detail(client_id: str):
    """Get detailed client information"""
    try:
        case_mgmt_db.connect()
        cursor = case_mgmt_db.connection.cursor()
        
        # Get client details with related data
        cursor.execute("""
            SELECT c.*, 
                   COUNT(r.referral_id) as total_referrals,
                   SUM(CASE WHEN r.status IN ('Pending', 'Active') THEN 1 ELSE 0 END) as active_referrals,
                   SUM(CASE WHEN r.status = 'Completed' THEN 1 ELSE 0 END) as completed_referrals,
                   COUNT(t.task_id) as total_tasks,
                   SUM(CASE WHEN t.status = 'Pending' THEN 1 ELSE 0 END) as pending_tasks
            FROM clients c
            LEFT JOIN service_referrals r ON c.client_id = r.client_id
            LEFT JOIN case_management_tasks t ON c.client_id = t.client_id
            WHERE c.client_id = ?
            GROUP BY c.client_id
        """, (client_id,))
        
        client_row = cursor.fetchone()
        if not client_row:
            return jsonify({
                'success': False,
                'error': 'Client not found'
            }), 404
        
        client_data = dict(client_row)
        
        # Get recent referrals
        cursor.execute("""
            SELECT r.*, p.name as provider_name, s.service_category, s.service_type
            FROM service_referrals r
            JOIN service_providers p ON r.provider_id = p.provider_id
            JOIN social_services s ON r.service_id = s.service_id
            WHERE r.client_id = ?
            ORDER BY r.referral_date DESC
            LIMIT 10
        """, (client_id,))
        
        referrals = [dict(row) for row in cursor.fetchall()]
        
        # Get recent tasks
        cursor.execute("""
            SELECT * FROM case_management_tasks
            WHERE client_id = ?
            ORDER BY created_at DESC
            LIMIT 10
        """, (client_id,))
        
        tasks = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'client': client_data,
            'referrals': referrals,
            'tasks': tasks
        })
        
    except Exception as e:
        logger.error(f"Get client detail error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/clients/<client_id>', methods=['PUT'])
def api_update_client(client_id: str):
    """Update client information"""
    try:
        data = request.get_json()
        case_mgmt_db.connect()
        
        # Build update query dynamically
        update_fields = []
        params = []
        
        updatable_fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender', 'primary_phone', 'email',
            'address', 'city', 'county', 'zip_code', 'emergency_contact', 'emergency_phone',
            'is_veteran', 'has_disability', 'special_populations', 'background_summary',
            'sobriety_status', 'insurance_status', 'housing_status', 'employment_status',
            'service_priorities', 'risk_level', 'discharge_date', 'notes'
        ]
        
        for field in updatable_fields:
            if field in data:
                update_fields.append(f"{field} = ?")
                params.append(data[field])
        
        if not update_fields:
            return jsonify({
                'success': False,
                'error': 'No valid fields to update'
            }), 400
        
        # Add last_updated timestamp
        update_fields.append("last_updated = ?")
        params.append(datetime.now().isoformat())
        params.append(client_id)
        
        # Execute update
        cursor = case_mgmt_db.connection.cursor()
        cursor.execute(f"""
            UPDATE clients 
            SET {', '.join(update_fields)}
            WHERE client_id = ?
        """, params)
        
        case_mgmt_db.connection.commit()
        
        # Get updated client data
        cursor.execute("SELECT * FROM clients WHERE client_id = ?", (client_id,))
        updated_client = dict(cursor.fetchone())
        
        # Broadcast update
        socketio.emit('client_updated', {
            'type': 'client_updated',
            'client': updated_client,
            'timestamp': datetime.now().isoformat()
        }, room=f"cm_{updated_client['case_manager_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Client updated successfully',
            'client': updated_client
        })
        
    except Exception as e:
        logger.error(f"Update client error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# REFERRAL MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/referrals', methods=['GET'])
def api_get_referrals():
    """Get filtered list of referrals for case manager"""
    try:
        case_manager_id = request.args.get('case_manager_id', 'default_cm')
        status = request.args.get('status', '')
        priority = request.args.get('priority', '')
        client_id = request.args.get('client_id', '')
        days_filter = request.args.get('days', '')  # e.g., 'overdue', 'recent'
        
        # Build query with filters
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
                   p.name as provider_name,
                   s.service_category,
                   s.service_type,
                   julianday('now') - julianday(r.referral_date) as days_since_referral
            FROM service_referrals r
            JOIN clients c ON r.client_id = c.client_id
            JOIN service_providers p ON r.provider_id = p.provider_id
            JOIN social_services s ON r.service_id = s.service_id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY r.referral_date DESC
        """
        
        case_mgmt_db.connect()
        cursor = case_mgmt_db.connection.cursor()
        cursor.execute(query, params)
        
        referrals = [dict(row) for row in cursor.fetchall()]
        
        return jsonify({
            'success': True,
            'referrals': referrals,
            'total_count': len(referrals)
        })
        
    except Exception as e:
        logger.error(f"Get referrals error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'referrals': []
        }), 500

@app.route('/api/referrals', methods=['POST'])
def api_create_referral():
    """Create a new service referral"""
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
        
        # Create referral object
        referral = ServiceReferral(**data)
        
        # Save to database
        referral_db_id = case_mgmt_db.save_referral(referral)
        
        # Create automatic follow-up task
        follow_up_task = CaseManagementTask(
            case_manager_id=referral.case_manager_id,
            client_id=referral.client_id,
            referral_id=referral.referral_id,
            task_type='Follow-up',
            title=f'Follow up on {data.get("service_type", "service")} referral',
            description=f'Check status of referral to {data.get("provider_name", "provider")}',
            priority=referral.priority_level,
            due_date=(datetime.now() + timedelta(days=3)).isoformat(),
            is_automated=True,
            created_by=referral.case_manager_id
        )
        
        case_mgmt_db.save_task(follow_up_task)
        
        # Broadcast updates
        socketio.emit('referral_created', {
            'type': 'referral_created',
            'referral': referral.to_dict(),
            'task': follow_up_task.to_dict(),
            'timestamp': datetime.now().isoformat()
        }, room=f"cm_{referral.case_manager_id}")
        
        return jsonify({
            'success': True,
            'message': 'Referral created successfully',
            'referral_id': referral.referral_id,
            'follow_up_task_id': follow_up_task.task_id
        })
        
    except Exception as e:
        logger.error(f"Create referral error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/referrals/<referral_id>/status', methods=['PUT'])
def api_update_referral_status(referral_id: str):
    """Update referral status"""
    try:
        data = request.get_json()
        new_status = data.get('status')
        notes = data.get('notes', '')
        completion_date = data.get('completion_date', '')
        
        if not new_status:
            return jsonify({
                'success': False,
                'error': 'Status is required'
            }), 400
        
        case_mgmt_db.connect()
        cursor = case_mgmt_db.connection.cursor()
        
        # Update referral status
        update_fields = ["status = ?", "last_updated = ?"]
        params = [new_status, datetime.now().isoformat()]
        
        if notes:
            update_fields.append("notes = ?")
            params.append(notes)
            
        if completion_date and new_status == 'Completed':
            update_fields.append("completion_date = ?")
            params.append(completion_date)
        
        params.append(referral_id)
        
        cursor.execute(f"""
            UPDATE service_referrals 
            SET {', '.join(update_fields)}
            WHERE referral_id = ?
        """, params)
        
        case_mgmt_db.connection.commit()
        
        # Get updated referral data
        cursor.execute("""
            SELECT r.*, c.first_name || ' ' || c.last_name as client_name,
                   p.name as provider_name, s.service_type
            FROM service_referrals r
            JOIN clients c ON r.client_id = c.client_id
            JOIN service_providers p ON r.provider_id = p.provider_id
            JOIN social_services s ON r.service_id = s.service_id
            WHERE r.referral_id = ?
        """, (referral_id,))
        
        updated_referral = dict(cursor.fetchone())
        
        # Broadcast update
        socketio.emit('referral_updated', {
            'type': 'referral_status_changed',
            'referral': updated_referral,
            'timestamp': datetime.now().isoformat()
        }, room=f"cm_{updated_referral['case_manager_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Referral status updated successfully',
            'referral': updated_referral
        })
        
    except Exception as e:
        logger.error(f"Update referral status error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# TASK MANAGEMENT API ENDPOINTS
# =============================================================================

@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    """Get filtered list of tasks for case manager"""
    try:
        case_manager_id = request.args.get('case_manager_id', 'default_cm')
        status = request.args.get('status', '')
        priority = request.args.get('priority', '')
        task_type = request.args.get('task_type', '')
        client_id = request.args.get('client_id', '')
        due_filter = request.args.get('due', '')  # 'overdue', 'today', 'week'
        
        # Build query with filters
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
                   julianday(t.due_date) - julianday('now') as days_until_due
            FROM case_management_tasks t
            LEFT JOIN clients c ON t.client_id = c.client_id
            WHERE {' AND '.join(where_conditions)}
            ORDER BY 
                CASE WHEN t.status = 'Overdue' THEN 1
                     WHEN t.priority = 'Urgent' THEN 2
                     WHEN t.priority = 'High' THEN 3
                     ELSE 4 END,
                t.due_date ASC
        """
        
        case_mgmt_db.connect()
        cursor = case_mgmt_db.connection.cursor()
        cursor.execute(query, params)
        
        tasks = [dict(row) for row in cursor.fetchall()]
        
        # Update overdue tasks status
        for task in tasks:
            if (task['status'] != 'Completed' and 
                task['due_date'] and 
                datetime.fromisoformat(task['due_date']) < datetime.now()):
                task['status'] = 'Overdue'
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'total_count': len(tasks)
        })
        
    except Exception as e:
        logger.error(f"Get tasks error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'tasks': []
        }), 500

@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['case_manager_id', 'title']
        for field in required_fields:
            if not data.get(field):
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Create task object
        task = CaseManagementTask(**data)
        
        # Save to database
        task_db_id = case_mgmt_db.save_task(task)
        
        # Broadcast update
        socketio.emit('task_created', {
            'type': 'task_created',
            'task': task.to_dict(),
            'timestamp': datetime.now().isoformat()
        }, room=f"cm_{task.case_manager_id}")
        
        return jsonify({
            'success': True,
            'message': 'Task created successfully',
            'task_id': task.task_id,
            'task': task.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Create task error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/tasks/<task_id>/complete', methods=['PUT'])
def api_complete_task(task_id: str):
    """Mark task as completed"""
    try:
        data = request.get_json()
        completion_notes = data.get('completion_notes', '')
        time_spent = data.get('time_spent_minutes', 0)
        
        case_mgmt_db.connect()
        cursor = case_mgmt_db.connection.cursor()
        
        # Update task status
        cursor.execute("""
            UPDATE case_management_tasks 
            SET status = 'Completed',
                completed_date = ?,
                completion_notes = ?,
                time_spent_minutes = ?,
                last_updated = ?
            WHERE task_id = ?
        """, (
            datetime.now().isoformat(),
            completion_notes,
            time_spent,
            datetime.now().isoformat(),
            task_id
        ))
        
        case_mgmt_db.connection.commit()
        
        # Get updated task data
        cursor.execute("""
            SELECT t.*, 
                   COALESCE(c.first_name || ' ' || c.last_name, 'No Client') as client_name
            FROM case_management_tasks t
            LEFT JOIN clients c ON t.client_id = c.client_id
            WHERE t.task_id = ?
        """, (task_id,))
        
        updated_task = dict(cursor.fetchone())
        
        # Broadcast update
        socketio.emit('task_completed', {
            'type': 'task_completed',
            'task': updated_task,
            'timestamp': datetime.now().isoformat()
        }, room=f"cm_{updated_task['case_manager_id']}")
        
        return jsonify({
            'success': True,
            'message': 'Task completed successfully',
            'task': updated_task
        })
        
    except Exception as e:
        logger.error(f"Complete task error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# =============================================================================
# WORKFLOW AUTOMATION API ENDPOINTS
# =============================================================================

@app.route('/api/automation/follow-up', methods=['POST'])
def api_create_automated_follow_ups():
    """Create automated follow-up tasks"""
    try:
        automation = WorkflowAutomation("databases/social_services.db")
        created_tasks = automation.create_automated_follow_up_tasks()
        automation.close()
        
        # Broadcast to all connected case managers
        for task_id in created_tasks:
            # Get task details to find case manager
            case_mgmt_db.connect()
            cursor = case_mgmt_db.connection.cursor()
            cursor.execute("SELECT * FROM case_management_tasks WHERE task_id = ?", (task_id,))
            task_data = dict(cursor.fetchone())
            
            socketio.emit('automated_task_created', {
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

@app.route('/api/automation/escalate', methods=['POST'])
def api_escalate_overdue():
    """Escalate overdue referrals"""
    try:
        automation = WorkflowAutomation("databases/social_services.db")
        escalated_referrals = automation.check_and_escalate_overdue_referrals()
        automation.close()
        
        return jsonify({
            'success': True,
            'message': f'Escalated {len(escalated_referrals)} overdue referrals',
            'escalated_referrals': escalated_referrals
        })
        
    except Exception as e:
        logger.error(f"Escalation error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'escalated_referrals': []
        }), 500

# =============================================================================
# ANALYTICS AND REPORTING API ENDPOINTS
# =============================================================================

@app.route('/api/analytics/performance/<case_manager_id>')
def api_performance_analytics(case_manager_id: str):
    """Get detailed performance analytics"""
    try:
        period_days = request.args.get('period', 30, type=int)
        
        metrics = PerformanceMetrics("databases/social_services.db")
        performance_data = metrics.get_case_manager_performance(case_manager_id, period_days)
        metrics.close()
        
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

@app.route('/api/analytics/providers')
def api_provider_analytics():
    """Get provider network performance analysis"""
    try:
        provider_id = request.args.get('provider_id')
        
        metrics = PerformanceMetrics("databases/social_services.db")
        provider_data = metrics.get_provider_performance_analysis(provider_id)
        metrics.close()
        
        return jsonify({
            'success': True,
            'provider_analysis': provider_data
        })
        
    except Exception as e:
        logger.error(f"Provider analytics error: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'provider_analysis': {}
        }), 500

# =============================================================================
# BACKGROUND AUTOMATION TASKS
# =============================================================================

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
# ERROR HANDLERS
# =============================================================================

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

# =============================================================================
# MAIN ROUTE FOR DASHBOARD
# =============================================================================

@app.route('/services')
def services_dashboard():
    """Main dashboard route"""
    return render_template('services_dashboard.html')

# =============================================================================
# APPLICATION ENTRY POINT
# =============================================================================

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Ensure database directory exists
    os.makedirs('databases', exist_ok=True)
    
    # Initialize databases
    try:
        services_db.create_tables()
        case_mgmt_db.ensure_case_management_tables()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
    
    # Run the application
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=5002, 
        debug=True,
        allow_unsafe_werkzeug=True
    )