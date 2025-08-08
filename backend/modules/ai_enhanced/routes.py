"""
AI API Routes for Second Chance Jobs Platform.

This module provides REST API endpoints for AI-powered features including
intelligent chat, task analysis, and automated workflow suggestions.
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field

from ...core.container import get_container
from ...shared.auth.dependencies import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["AI"])


# Request/Response Models
class ChatRequest(BaseModel):
    message: str = Field(..., description="User message")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    client_id: Optional[str] = Field(default=None, description="Client ID for context")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")


class ChatResponse(BaseModel):
    response: str = Field(..., description="AI response")
    conversation_id: str = Field(..., description="Conversation ID")
    function_calls: Optional[List[Dict[str, Any]]] = Field(default=None, description="Function calls made")
    context_used: Optional[Dict[str, Any]] = Field(default=None, description="Context information used")


class TextAnalysisRequest(BaseModel):
    text: str = Field(..., description="Text to analyze")
    analysis_type: str = Field(default="sentiment", description="Type of analysis")


class TextAnalysisResponse(BaseModel):
    analysis_type: str
    result: Dict[str, Any]
    timestamp: str


class SmartRemindersRequest(BaseModel):
    client_id: str = Field(..., description="Client ID")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class SmartRemindersResponse(BaseModel):
    client_id: str
    reminders: List[Dict[str, Any]]
    generated_at: str


@router.post("/chat", response_model=ChatResponse)
async def ai_chat(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    AI-powered chat interface for case managers and clients.
    
    Provides intelligent assistance with:
    - Task management
    - Resource recommendations
    - Workflow guidance
    - Client support
    """
    try:
        container = get_container()
        ai_service = container.get_service("ai")
        
        # Build context
        context = request.context or {}
        context.update({
            "user_id": current_user["id"],
            "user_role": current_user["role"],
            "client_id": request.client_id
        })
        
        # Generate AI response
        response = await ai_service.generate_response(
            prompt=request.message,
            context=context
        )
        
        # Generate conversation ID if not provided
        conversation_id = request.conversation_id or f"conv_{current_user['id']}_{int(datetime.now().timestamp())}"
        
        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            context_used=context
        )
        
    except Exception as e:
        logger.error(f"Error in AI chat: {e}")
        raise HTTPException(status_code=500, detail="AI chat service unavailable")


@router.post("/analyze", response_model=TextAnalysisResponse)
async def analyze_text(
    request: TextAnalysisRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Analyze text using AI for various purposes.
    
    Supported analysis types:
    - sentiment: Sentiment analysis
    - risk: Risk factor analysis
    - urgency: Urgency level assessment
    - priority: Priority scoring
    - category: Content categorization
    """
    try:
        container = get_container()
        ai_service = container.get_service("ai")
        
        # Perform analysis
        result = await ai_service.analyze_text(
            text=request.text,
            analysis_type=request.analysis_type
        )
        
        return TextAnalysisResponse(
            analysis_type=request.analysis_type,
            result=result,
            timestamp=result.get("timestamp", "")
        )
        
    except Exception as e:
        logger.error(f"Error in text analysis: {e}")
        raise HTTPException(status_code=500, detail="Text analysis service unavailable")


@router.post("/reminders/generate", response_model=SmartRemindersResponse)
async def generate_smart_reminders(
    request: SmartRemindersRequest,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Generate intelligent reminders for a client using AI analysis.
    
    Analyzes client situation and generates contextually relevant,
    prioritized reminders and tasks.
    """
    try:
        container = get_container()
        ai_service = container.get_service("ai")
        
        # Generate smart reminders
        reminders = await ai_service.generate_smart_reminders(
            client_id=request.client_id,
            context=request.context
        )
        
        from datetime import datetime
        return SmartRemindersResponse(
            client_id=request.client_id,
            reminders=reminders,
            generated_at=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"Error generating smart reminders: {e}")
        raise HTTPException(status_code=500, detail="Smart reminders service unavailable")


@router.post("/function-call")
async def execute_function_call(
    function_name: str,
    parameters: Dict[str, Any],
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Execute a specific AI function call directly.
    
    Allows direct access to AI function capabilities for
    advanced integrations and custom workflows.
    """
    try:
        container = get_container()
        ai_service = container.get_service("ai")
        
        # Add user context to parameters
        parameters.update({
            "user_id": current_user["id"],
            "user_role": current_user["role"]
        })
        
        # Execute function
        result = await ai_service.function_call(function_name, parameters)
        
        return {
            "function_name": function_name,
            "parameters": parameters,
            "result": result,
            "executed_by": current_user["id"]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error executing function call: {e}")
        raise HTTPException(status_code=500, detail="Function execution failed")


@router.get("/functions")
async def list_available_functions(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    List all available AI functions and their descriptions.
    
    Provides documentation for available AI function calls
    that can be used in chat or direct function execution.
    """
    try:
        container = get_container()
        ai_service = container.get_service("ai")
        
        # Get function definitions
        functions = ai_service._get_function_definitions()
        
        return {
            "available_functions": functions,
            "total_count": len(functions),
            "user_role": current_user["role"]
        }
        
    except Exception as e:
        logger.error(f"Error listing functions: {e}")
        raise HTTPException(status_code=500, detail="Unable to list functions")


@router.get("/health")
async def ai_health_check():
    """Health check endpoint for AI services."""
    try:
        container = get_container()
        ai_service = container.get_service("ai")
        
        # Check if AI service is initialized
        if not ai_service._initialized:
            await ai_service.initialize()
        
        return {
            "status": "healthy",
            "service": "ai",
            "initialized": ai_service._initialized,
            "functions_registered": len(ai_service.function_registry)
        }
        
    except Exception as e:
        logger.error(f"AI health check failed: {e}")
        return {
            "status": "unhealthy",
            "service": "ai",
            "error": str(e)
        }

