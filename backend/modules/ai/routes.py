#!/usr/bin/env python3
"""
AI Routes - FastAPI Router for Second Chance Jobs Platform
AI Assistant and chat functionality for case management
"""

from fastapi import APIRouter, HTTPException, Request, Depends, Query, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Dict, List, Any, Optional
import logging
import json
import sys
import os
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from ai.simple_assistant import SimpleAIAssistant

logger = logging.getLogger(__name__)

# Create FastAPI router
router = APIRouter(tags=["ai"])

# Initialize AI assistant
ai_assistant = None

def get_ai_assistant():
    """Get thread-safe AI assistant instance"""
    global ai_assistant
    if ai_assistant is None:
        ai_assistant = SimpleAIAssistant()
    return ai_assistant

# Pydantic models
class ChatMessage(BaseModel):
    message: str
    client_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: str

@router.get("/")
async def ai_dashboard():
    """AI assistant dashboard"""
    return {"message": "AI Assistant API Ready", "endpoints": ["/chat", "/conversations"]}

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(chat_request: ChatMessage):
    """Send message to AI assistant and get response"""
    try:
        assistant = get_ai_assistant()
        
        # Generate conversation ID if not provided
        conversation_id = chat_request.context.get("conversation_id", f"conv_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Get AI response
        response = assistant.get_response(
            message=chat_request.message,
            conversation_id=conversation_id,
            client_id=chat_request.client_id,
            context=chat_request.context
        )
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(status_code=500, detail=f"AI chat error: {str(e)}")

@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get conversation history"""
    try:
        assistant = get_ai_assistant()
        
        if conversation_id in assistant.conversations:
            return {
                "conversation_id": conversation_id,
                "messages": assistant.conversations[conversation_id],
                "message_count": len(assistant.conversations[conversation_id])
            }
        else:
            return {
                "conversation_id": conversation_id,
                "messages": [],
                "message_count": 0
            }
            
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation retrieval error: {str(e)}")

@router.get("/conversations")
async def list_conversations():
    """List all active conversations"""
    try:
        assistant = get_ai_assistant()
        
        conversations_summary = []
        for conv_id, messages in assistant.conversations.items():
            if messages:
                conversations_summary.append({
                    "conversation_id": conv_id,
                    "message_count": len(messages),
                    "last_message": messages[-1].get("content", "")[:100] if messages else "",
                    "timestamp": messages[-1].get("timestamp", "") if messages else ""
                })
        
        return {
            "conversations": conversations_summary,
            "total_conversations": len(conversations_summary)
        }
        
    except Exception as e:
        logger.error(f"Error listing conversations: {e}")
        raise HTTPException(status_code=500, detail=f"Conversations listing error: {str(e)}")

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation"""
    try:
        assistant = get_ai_assistant()
        
        if conversation_id in assistant.conversations:
            del assistant.conversations[conversation_id]
            return {"message": f"Conversation {conversation_id} deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="Conversation not found")
            
    except Exception as e:
        logger.error(f"Error deleting conversation: {e}")
        raise HTTPException(status_code=500, detail=f"Conversation deletion error: {str(e)}")

@router.post("/analyze/client/{client_id}")
async def analyze_client_situation(client_id: str, analysis_request: Dict[str, Any] = Body(...)):
    """AI analysis of client situation and recommendations"""
    try:
        assistant = get_ai_assistant()
        
        # Create analysis prompt
        analysis_prompt = f"""
        Please analyze the situation for client {client_id} and provide recommendations.
        Analysis request: {json.dumps(analysis_request, indent=2)}
        
        Please provide:
        1. Situation assessment
        2. Priority recommendations
        3. Next steps
        4. Potential challenges and solutions
        """
        
        response = assistant.get_response(
            message=analysis_prompt,
            conversation_id=f"analysis_{client_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            client_id=client_id,
            context=analysis_request
        )
        
        return {
            "client_id": client_id,
            "analysis": response,
            "timestamp": datetime.now().isoformat(),
            "request_context": analysis_request
        }
        
    except Exception as e:
        logger.error(f"Error in client analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Client analysis error: {str(e)}")

@router.get("/health")
async def ai_health_check():
    """Health check for AI assistant"""
    try:
        assistant = get_ai_assistant()
        
        # Simple test message
        test_response = assistant.get_response(
            message="Health check - please respond with 'OK'",
            conversation_id="health_check",
            client_id=None,
            context={}
        )
        
        return {
            "status": "healthy",
            "ai_responsive": "OK" in test_response or "ok" in test_response.lower(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }