"""
Database components for Case Management Suite
"""

from .session import get_async_session
from .models import Task, Client, User, TaskPriority, TaskStatus

# Import new database access layer components
from .new_access_layer import (
    db_access, 
    core_clients_service, 
    ai_service,
    DatabaseAccessLayer,
    CoreClientsService,
    AIAssistantService
)

# Import integrity manager
from .db_integrity_manager import get_integrity_manager

# Import integrity routes
from .integrity_routes import router as integrity_router

__all__ = [
    'get_async_session', 'Task', 'Client', 'User', 'TaskPriority', 'TaskStatus',
    'db_access', 'core_clients_service', 'ai_service',
    'DatabaseAccessLayer', 'CoreClientsService', 'AIAssistantService',
    'get_integrity_manager', 'integrity_router'
]