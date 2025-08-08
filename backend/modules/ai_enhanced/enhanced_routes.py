"""
Enhanced AI Routes for Case Management Suite
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging

from .enhanced_service import AIService

logger = logging.getLogger(__name__)
router = APIRouter()

# Pydantic models
class ChatRequest(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    function_calls: Optional[List[Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None

class AnalyzeRequest(BaseModel):
    text: str
    analysis_type: str = "sentiment"
    context: Optional[Dict[str, Any]] = None

class AnalyzeResponse(BaseModel):
    analysis: Dict[str, Any]
    sentiment: Optional[str] = None
    confidence: Optional[float] = None

class FunctionCallRequest(BaseModel):
    function_name: str
    parameters: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None

# Initialize AI service
ai_service = AIService()

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Chat with the AI assistant"""
    try:
        response = await ai_service.generate_response(
            prompt=request.message,
            context=request.context or {}
        )
        return ChatResponse(
            response=response,
            context=request.context
        )
    except Exception as e:
        logger.error(f"AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    """Analyze text using AI"""
    try:
        analysis = await ai_service.analyze_text(
            text=request.text,
            analysis_type=request.analysis_type
        )
        return AnalyzeResponse(
            analysis=analysis,
            sentiment=analysis.get("sentiment"),
            confidence=analysis.get("confidence")
        )
    except Exception as e:
        logger.error(f"Text analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/function-call")
async def call_function(request: FunctionCallRequest):
    """Call a specific AI function"""
    try:
        result = await ai_service.function_call(
            function_name=request.function_name,
            parameters=request.parameters
        )
        return {"result": result}
    except Exception as e:
        logger.error(f"Function call error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/functions")
async def get_available_functions():
    """Get list of available AI functions"""
    try:
        functions = ai_service.function_registry.keys()
        return {"functions": list(functions)}
    except Exception as e:
        logger.error(f"Get functions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def ai_health_check():
    """Health check for AI service"""
    try:
        await ai_service.initialize()
        return {"status": "healthy", "service": "enhanced_ai"}
    except Exception as e:
        logger.error(f"AI health check error: {e}")
        return {"status": "unhealthy", "error": str(e)}

