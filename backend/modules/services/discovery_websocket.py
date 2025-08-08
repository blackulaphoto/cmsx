#!/usr/bin/env python3
"""
Discovery WebSocket Handler
Real-time updates for service discovery progress
"""

import logging
import json
from typing import Dict, Any
from flask_socketio import emit, join_room, leave_room
from .auto_discovery import get_auto_discovery_engine

logger = logging.getLogger(__name__)

class DiscoveryWebSocketHandler:
    """Handle WebSocket connections for discovery updates"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('join_discovery_room')
        def handle_join_discovery_room(data):
            """Join a discovery room for updates"""
            task_id = data.get('task_id')
            if task_id:
                join_room(f"discovery_{task_id}")
                emit('discovery_room_joined', {'task_id': task_id})
                logger.info(f"Client joined discovery room: {task_id}")
        
        @self.socketio.on('leave_discovery_room')
        def handle_leave_discovery_room(data):
            """Leave a discovery room"""
            task_id = data.get('task_id')
            if task_id:
                leave_room(f"discovery_{task_id}")
                emit('discovery_room_left', {'task_id': task_id})
                logger.info(f"Client left discovery room: {task_id}")
        
        @self.socketio.on('get_discovery_status')
        def handle_get_discovery_status(data):
            """Get current discovery status"""
            task_id = data.get('task_id')
            if task_id:
                try:
                    auto_discovery = get_auto_discovery_engine()
                    status = auto_discovery.get_discovery_status(task_id)
                    emit('discovery_status_update', {
                        'task_id': task_id,
                        'status': status
                    })
                except Exception as e:
                    logger.error(f"Error getting discovery status: {e}")
                    emit('discovery_error', {
                        'task_id': task_id,
                        'error': str(e)
                    })
    
    def broadcast_discovery_update(self, task_id: str, status: Dict[str, Any]):
        """Broadcast discovery update to all clients in the room"""
        try:
            self.socketio.emit('discovery_status_update', {
                'task_id': task_id,
                'status': status
            }, room=f"discovery_{task_id}")
            logger.debug(f"Broadcasted discovery update for task {task_id}")
        except Exception as e:
            logger.error(f"Error broadcasting discovery update: {e}")
    
    def broadcast_discovery_complete(self, task_id: str, results: Dict[str, Any]):
        """Broadcast discovery completion"""
        try:
            self.socketio.emit('discovery_complete', {
                'task_id': task_id,
                'results': results
            }, room=f"discovery_{task_id}")
            logger.info(f"Broadcasted discovery completion for task {task_id}")
        except Exception as e:
            logger.error(f"Error broadcasting discovery completion: {e}")
    
    def broadcast_discovery_error(self, task_id: str, error: str):
        """Broadcast discovery error"""
        try:
            self.socketio.emit('discovery_error', {
                'task_id': task_id,
                'error': error
            }, room=f"discovery_{task_id}")
            logger.error(f"Broadcasted discovery error for task {task_id}: {error}")
        except Exception as e:
            logger.error(f"Error broadcasting discovery error: {e}")

# Global instance
discovery_websocket_handler = None

def setup_discovery_websocket(socketio):
    """Setup discovery WebSocket handler"""
    global discovery_websocket_handler
    discovery_websocket_handler = DiscoveryWebSocketHandler(socketio)
    return discovery_websocket_handler

def get_discovery_websocket_handler():
    """Get the discovery WebSocket handler"""
    return discovery_websocket_handler