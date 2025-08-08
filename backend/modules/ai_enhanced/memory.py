"""
AI Conversation Memory System for Second Chance Jobs Platform.

This module provides persistent conversation memory, context management,
and intelligent conversation continuity for the AI assistant.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timezone, timedelta
from uuid import UUID, uuid4
import uuid

from ...core.config import settings
from ...core.container import singleton
from ...shared.database.session import get_async_session

logger = logging.getLogger(__name__)


class ConversationMemory:
    """
    Persistent conversation memory for AI assistant.
    
    Manages conversation history, context, and intelligent memory
    for continuous and contextual AI interactions.
    """
    
    def __init__(self):
        self.max_conversation_length = 50  # Maximum messages to keep in active memory
        self.context_window_hours = 24  # Hours to consider for recent context
        self.memory_compression_threshold = 100  # Messages before compression
        
    async def get_conversation_history(self, client_id: str, user_id: str, 
                                     limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get conversation history for a client-user pair.
        
        Args:
            client_id: Client ID
            user_id: User ID (case manager)
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of conversation messages with context
        """
        try:
            # This would query the database for conversation history
            # For now, return mock conversation data
            conversation_history = [
                {
                    "id": "msg_1",
                    "conversation_id": f"conv_{client_id}_{user_id}",
                    "client_id": client_id,
                    "user_id": user_id,
                    "message_type": "user",
                    "content": "Can you help me understand John's housing situation?",
                    "timestamp": "2024-01-22T10:00:00Z",
                    "context": {
                        "client_name": "John Doe",
                        "current_module": "housing",
                        "referenced_entities": ["housing_application_1"]
                    }
                },
                {
                    "id": "msg_2",
                    "conversation_id": f"conv_{client_id}_{user_id}",
                    "client_id": client_id,
                    "user_id": user_id,
                    "message_type": "assistant",
                    "content": "Based on John's profile, he currently has an active transitional housing application submitted on January 15th. He's been approved for emergency shelter and is on the waiting list for permanent supportive housing. His housing risk score is Medium due to stable income but past eviction history.",
                    "timestamp": "2024-01-22T10:00:15Z",
                    "context": {
                        "client_name": "John Doe",
                        "current_module": "housing",
                        "referenced_entities": ["housing_application_1", "risk_assessment_1"],
                        "function_calls": ["get_client_housing_summary"],
                        "data_sources": ["housing_applications", "risk_assessments"]
                    }
                },
                {
                    "id": "msg_3",
                    "conversation_id": f"conv_{client_id}_{user_id}",
                    "client_id": client_id,
                    "user_id": user_id,
                    "message_type": "user",
                    "content": "What tasks should I prioritize for him this week?",
                    "timestamp": "2024-01-22T10:01:00Z",
                    "context": {
                        "client_name": "John Doe",
                        "current_module": "reminders",
                        "conversation_context": "continuing_housing_discussion"
                    }
                }
            ]
            
            # Apply limit
            conversation_history = conversation_history[-limit:]
            
            logger.info(f"Retrieved {len(conversation_history)} conversation messages")
            return conversation_history
            
        except Exception as e:
            logger.error(f"Error getting conversation history: {e}")
            raise
    
    async def save_conversation_message(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a conversation message with context.
        
        Args:
            conversation_data: Message data with context
            
        Returns:
            Saved message data
        """
        try:
            # Generate message ID
            message_id = str(uuid4())
            
            # Add metadata
            message_data = {
                "id": message_id,
                "conversation_id": conversation_data.get("conversation_id"),
                "client_id": conversation_data.get("client_id"),
                "user_id": conversation_data.get("user_id"),
                "message_type": conversation_data.get("message_type"),  # user, assistant, system
                "content": conversation_data.get("content"),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "context": conversation_data.get("context", {}),
                "metadata": {
                    "tokens_used": conversation_data.get("tokens_used"),
                    "function_calls": conversation_data.get("function_calls", []),
                    "data_sources": conversation_data.get("data_sources", []),
                    "confidence_score": conversation_data.get("confidence_score"),
                    "response_time_ms": conversation_data.get("response_time_ms")
                }
            }
            
            # This would save to database
            # For now, just return the message data
            
            logger.info(f"Saved conversation message {message_id}")
            return message_data
            
        except Exception as e:
            logger.error(f"Error saving conversation message: {e}")
            raise
    
    async def get_conversation_context(self, client_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive conversation context for AI assistant.
        
        Args:
            client_id: Client ID
            user_id: User ID
            
        Returns:
            Conversation context including history, client data, and recent activities
        """
        try:
            # Get recent conversation history
            recent_messages = await self.get_conversation_history(
                client_id=client_id,
                user_id=user_id,
                limit=10
            )
            
            # Get client context data
            client_context = await self._get_client_context(client_id)
            
            # Get recent activities
            recent_activities = await self._get_recent_activities(client_id)
            
            # Get conversation summary
            conversation_summary = await self._get_conversation_summary(client_id, user_id)
            
            # Build comprehensive context
            context = {
                "conversation_id": f"conv_{client_id}_{user_id}",
                "client_id": client_id,
                "user_id": user_id,
                "client_context": client_context,
                "recent_messages": recent_messages,
                "recent_activities": recent_activities,
                "conversation_summary": conversation_summary,
                "context_metadata": {
                    "last_interaction": recent_messages[0]["timestamp"] if recent_messages else None,
                    "total_messages": len(recent_messages),
                    "active_topics": self._extract_active_topics(recent_messages),
                    "pending_actions": await self._get_pending_actions(client_id),
                    "context_freshness": "current"
                }
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            raise
    
    async def update_conversation_context(self, client_id: str, user_id: str,
                                        context_updates: Dict[str, Any]) -> None:
        """
        Update conversation context with new information.
        
        Args:
            client_id: Client ID
            user_id: User ID
            context_updates: Context updates to apply
        """
        try:
            # This would update conversation context in database
            # Including topic tracking, entity mentions, action items, etc.
            
            logger.info(f"Updated conversation context for client {client_id}")
            
        except Exception as e:
            logger.error(f"Error updating conversation context: {e}")
            raise
    
    async def compress_conversation_memory(self, client_id: str, user_id: str) -> Dict[str, Any]:
        """
        Compress old conversation memory to maintain performance.
        
        Args:
            client_id: Client ID
            user_id: User ID
            
        Returns:
            Compression summary
        """
        try:
            # Get full conversation history
            full_history = await self.get_conversation_history(
                client_id=client_id,
                user_id=user_id,
                limit=1000
            )
            
            if len(full_history) < self.memory_compression_threshold:
                return {"status": "no_compression_needed", "message_count": len(full_history)}
            
            # Identify messages to compress (older than context window)
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=self.context_window_hours)
            
            messages_to_compress = []
            messages_to_keep = []
            
            for message in full_history:
                message_time = datetime.fromisoformat(message["timestamp"].replace('Z', '+00:00'))
                if message_time < cutoff_time:
                    messages_to_compress.append(message)
                else:
                    messages_to_keep.append(message)
            
            if not messages_to_compress:
                return {"status": "no_compression_needed", "message_count": len(full_history)}
            
            # Create compressed summary
            compressed_summary = await self._create_conversation_summary(messages_to_compress)
            
            # This would update database to replace old messages with summary
            
            compression_result = {
                "status": "compressed",
                "original_message_count": len(messages_to_compress),
                "retained_message_count": len(messages_to_keep),
                "compression_summary": compressed_summary,
                "compression_date": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Compressed conversation memory for client {client_id}")
            return compression_result
            
        except Exception as e:
            logger.error(f"Error compressing conversation memory: {e}")
            raise
    
    async def _get_client_context(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive client context for AI assistant."""
        
        # This would gather client data from all modules
        client_context = {
            "basic_info": {
                "name": "John Doe",
                "age": 35,
                "case_manager": "Sarah Johnson",
                "enrollment_date": "2024-01-01T00:00:00Z",
                "program_status": "active"
            },
            "risk_assessment": {
                "overall_risk": "medium",
                "housing_risk": "medium",
                "employment_risk": "low",
                "legal_risk": "high",
                "last_assessment": "2024-01-15T00:00:00Z"
            },
            "current_status": {
                "housing": "transitional_housing_application_pending",
                "employment": "job_searching",
                "legal": "probation_active",
                "benefits": "snap_approved_medicaid_pending"
            },
            "active_goals": [
                "Secure permanent housing",
                "Find stable employment",
                "Complete probation requirements",
                "Maintain sobriety"
            ],
            "recent_achievements": [
                "Completed job readiness training",
                "Submitted housing application",
                "Attended all court dates"
            ]
        }
        
        return client_context
    
    async def _get_recent_activities(self, client_id: str) -> List[Dict[str, Any]]:
        """Get recent client activities across all modules."""
        
        recent_activities = [
            {
                "date": "2024-01-22T09:00:00Z",
                "module": "housing",
                "activity": "Housing application status updated to 'under review'",
                "importance": "medium"
            },
            {
                "date": "2024-01-21T14:30:00Z",
                "module": "employment",
                "activity": "Applied for warehouse position at ABC Logistics",
                "importance": "high"
            },
            {
                "date": "2024-01-20T10:00:00Z",
                "module": "legal",
                "activity": "Completed weekly probation check-in",
                "importance": "high"
            },
            {
                "date": "2024-01-19T16:00:00Z",
                "module": "case_management",
                "activity": "Case note added: Client showing good progress",
                "importance": "low"
            }
        ]
        
        return recent_activities
    
    async def _get_conversation_summary(self, client_id: str, user_id: str) -> Dict[str, Any]:
        """Get conversation summary for context."""
        
        summary = {
            "key_topics_discussed": [
                "housing_applications",
                "job_search_progress",
                "probation_compliance",
                "benefit_applications"
            ],
            "action_items_created": [
                "Follow up on housing application",
                "Prepare for job interview",
                "Submit benefits documentation"
            ],
            "client_concerns_raised": [
                "Transportation to job interviews",
                "Housing application timeline",
                "Probation meeting schedule"
            ],
            "case_manager_notes": [
                "Client is motivated and engaged",
                "Needs support with transportation",
                "Making good progress on goals"
            ],
            "last_summary_date": "2024-01-22T00:00:00Z"
        }
        
        return summary
    
    def _extract_active_topics(self, messages: List[Dict[str, Any]]) -> List[str]:
        """Extract active topics from recent messages."""
        
        topics = set()
        
        for message in messages:
            context = message.get("context", {})
            current_module = context.get("current_module")
            if current_module:
                topics.add(current_module)
            
            # Extract topics from content (simplified)
            content = message.get("content", "").lower()
            if "housing" in content:
                topics.add("housing")
            if "job" in content or "employment" in content:
                topics.add("employment")
            if "court" in content or "legal" in content:
                topics.add("legal")
            if "benefit" in content:
                topics.add("benefits")
        
        return list(topics)
    
    async def _get_pending_actions(self, client_id: str) -> List[Dict[str, Any]]:
        """Get pending actions for the client."""
        
        pending_actions = [
            {
                "action": "Follow up on housing application",
                "due_date": "2024-01-25T00:00:00Z",
                "priority": "high",
                "module": "housing"
            },
            {
                "action": "Prepare for job interview",
                "due_date": "2024-01-24T00:00:00Z",
                "priority": "high",
                "module": "employment"
            },
            {
                "action": "Submit benefits documentation",
                "due_date": "2024-01-26T00:00:00Z",
                "priority": "medium",
                "module": "benefits"
            }
        ]
        
        return pending_actions
    
    async def _create_conversation_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a compressed summary of conversation messages."""
        
        # This would use AI to create an intelligent summary
        summary = {
            "time_period": {
                "start": messages[0]["timestamp"] if messages else None,
                "end": messages[-1]["timestamp"] if messages else None,
                "message_count": len(messages)
            },
            "key_topics": self._extract_active_topics(messages),
            "important_decisions": [
                "Decided to prioritize housing application follow-up",
                "Agreed to schedule job interview preparation session"
            ],
            "action_items_completed": [
                "Submitted housing application",
                "Updated resume with new template"
            ],
            "client_progress_notes": [
                "Client showing increased motivation",
                "Improved communication and engagement",
                "Successfully meeting deadlines"
            ],
            "summary_text": "Productive conversation period focused on housing and employment progress. Client demonstrated strong engagement and completed several important tasks. Key priorities identified for upcoming week.",
            "compressed_at": datetime.now(timezone.utc).isoformat()
        }
        
        return summary

