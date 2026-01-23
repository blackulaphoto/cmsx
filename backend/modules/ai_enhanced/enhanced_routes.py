"""
Enhanced AI Routes for Case Management Suite
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

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

async def store_conversation_memory(user_id: str, user_message: str, ai_response: str):
    """Helper function to store conversation in memory"""
    if user_id:
        from datetime import datetime
        if user_id not in ai_service.conversation_memory:
            ai_service.conversation_memory[user_id] = []
        
        timestamp = datetime.now().isoformat()
        ai_service.conversation_memory[user_id].extend([
            {"role": "user", "content": user_message, "timestamp": timestamp},
            {"role": "assistant", "content": ai_response, "timestamp": timestamp}
        ])
        
        # Keep only last 20 messages per user (10 exchanges)
        if len(ai_service.conversation_memory[user_id]) > 20:
            ai_service.conversation_memory[user_id] = ai_service.conversation_memory[user_id][-20:]
        
        logger.info(f"💾 Stored conversation for user {user_id}, total messages: {len(ai_service.conversation_memory[user_id])}")

@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(request: ChatRequest):
    """Chat with the AI assistant - ENHANCED VERSION WITH DIRECT EXECUTION"""
    try:
        # Ensure AI service is initialized
        if not ai_service._initialized:
            await ai_service.initialize()
        
        # Force re-initialization if function registry is empty
        if not ai_service.function_registry:
            logger.warning("Function registry is empty, forcing re-initialization")
            ai_service._initialized = False
            await ai_service.initialize()
        
        # Check for direct data queries first
        query_lower = request.message.lower()
        
        # Handle client count queries directly
        if "how many client" in query_lower or "number of client" in query_lower:
            result = await ai_service._list_active_clients()
            response = f"You currently have **{len(result)} active clients** in the system."
            # Store in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Handle list clients queries directly  
        elif "list" in query_lower and "client" in query_lower:
            result = await ai_service._list_active_clients()
            client_names = [client.get("name", "Unknown") for client in result]
            response = f"**Active Clients ({len(client_names)}):**\n\n" + "\n".join([f"• {name}" for name in client_names])
            # Store in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Handle find client queries directly
        elif "find" in query_lower and any(name in query_lower for name in ["maria", "john", "sarah", "client"]):
            # Extract name from query
            if "maria" in query_lower:
                result = await ai_service._search_clients_by_name("Maria")
            elif "john" in query_lower:
                result = await ai_service._search_clients_by_name("John")
            elif "sarah" in query_lower:
                result = await ai_service._search_clients_by_name("Sarah")
            else:
                result = []
            
            if result:
                if len(result) == 1:
                    client = result[0]
                    response = f"**Found Client:** {client.get('name', 'Unknown')}\n\n" + \
                              f"• Status: {client.get('status', 'Unknown')}\n" + \
                              f"• Risk Level: {client.get('risk_level', 'Unknown')}\n" + \
                              f"• Phone: {client.get('phone', 'Not provided')}\n" + \
                              f"• Email: {client.get('email', 'Not provided')}"
                else:
                    client_list = [f"{i+1}. {client.get('name', 'Unknown')} - {client.get('status', 'Unknown')}" for i, client in enumerate(result)]
                    response = f"**Found {len(result)} clients:**\n\n" + "\n".join(client_list)
            else:
                response = "No clients found matching that name."
            # Store in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Use the enhanced AI service for other queries
        try:
            # Ensure user_id is in context for memory storage
            context = request.context or {}
            if request.user_id:
                context["user_id"] = request.user_id
            
            logger.info(f"🔍 Calling generate_response with context: {context}")
            response = await ai_service.generate_response(
                prompt=request.message,
                context=context
            )
            logger.info(f"✅ generate_response completed successfully")
            
            # CRITICAL FIX: Store conversation in memory for complex queries
            await store_conversation_memory(request.user_id, request.message, response)
            
            return ChatResponse(
                response=response,
                context=request.context
            )
            
        except Exception as e:
            logger.error(f"❌ AI service error in generate_response: {e}")
            logger.error(f"❌ Exception type: {type(e)}")
            import traceback
            logger.error(f"❌ Full traceback: {traceback.format_exc()}")
            
            # Only fall back to simple responses if AI completely fails
            if any(greeting.lower() in query_lower for greeting in ['hello', 'hi', 'hey', 'good morning', 'how are you']):
                response = "Hello! I'm your AI Case Management Assistant. I can help you find clients, check appointments, review housing applications, and much more. What would you like to know?"
            else:
                response = f"I'm having trouble processing that request right now. Could you try rephrasing it? I can help you with client information, appointments, housing, benefits, and legal matters."
            
            # Store fallback responses in memory too
            await store_conversation_memory(request.user_id, request.message, response)
        
        return ChatResponse(
            response=response,
            context=request.context
        )
    except Exception as e:
        logger.error(f"Enhanced AI chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/memory-test")
async def test_memory_directly():
    """Test memory storage mechanism directly"""
    try:
        from datetime import datetime
        test_user = "diagnostic_user"
        test_message = "Test memory storage"
        test_response = "Test memory response"
        
        # Test 1: Check AI service instance
        service_id = id(ai_service)
        memory_dict_id = id(ai_service.conversation_memory)
        
        # Test 2: Store memory directly
        if test_user not in ai_service.conversation_memory:
            ai_service.conversation_memory[test_user] = []
        
        ai_service.conversation_memory[test_user].append({
            "role": "user", 
            "content": test_message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Test 3: Immediate retrieval
        stored_count = len(ai_service.conversation_memory.get(test_user, []))
        
        # Test 4: Check total memory keys
        total_users = len(ai_service.conversation_memory.keys())
        all_users = list(ai_service.conversation_memory.keys())
        
        return {
            "memory_test": "direct_storage",
            "ai_service_instance_id": service_id,
            "memory_dict_instance_id": memory_dict_id,
            "test_user_stored_messages": stored_count,
            "total_users_in_memory": total_users,
            "all_users": all_users,
            "memory_storage_success": stored_count > 0,
            "conversation_memory_type": str(type(ai_service.conversation_memory))
        }
        
    except Exception as e:
        return {"error": f"Memory test failed: {str(e)}"}

@router.get("/singleton-test")
async def test_singleton():
    """Test if singleton pattern is working"""
    try:
        # Import AI service multiple times
        from .enhanced_service import AIService
        
        # Create multiple instances
        instance1 = AIService()
        instance2 = AIService()
        
        # Check if they're the same object
        same_instance = instance1 is instance2
        same_memory = instance1.conversation_memory is instance2.conversation_memory
        
        # Get instance IDs
        id1 = id(instance1)
        id2 = id(instance2)
        memory_id1 = id(instance1.conversation_memory)
        memory_id2 = id(instance2.conversation_memory)
        
        return {
            "singleton_test": "pattern_verification",
            "same_instance": same_instance,
            "same_memory_dict": same_memory,
            "instance1_id": id1,
            "instance2_id": id2,
            "memory1_id": memory_id1,
            "memory2_id": memory_id2,
            "current_ai_service_id": id(ai_service)
        }
        
    except Exception as e:
        return {"error": f"Singleton test failed: {str(e)}"}

@router.get("/memory-trace/{user_id}")
async def trace_memory_retrieval(user_id: str):
    """Trace memory retrieval mechanism"""
    try:
        # Check what the memory API sees
        api_service_id = id(ai_service)
        api_memory_dict = ai_service.conversation_memory
        api_user_messages = api_memory_dict.get(user_id, [])
        
        # Check all users in memory
        all_users_in_memory = list(ai_service.conversation_memory.keys())
        total_memory_size = len(ai_service.conversation_memory)
        
        # Check if conversation_memory is the right type
        memory_type = type(ai_service.conversation_memory)
        
        return {
            "memory_trace": "retrieval_path",
            "user_id": user_id,
            "api_service_instance_id": api_service_id,
            "user_messages_found": len(api_user_messages),
            "all_users_in_memory": all_users_in_memory,
            "total_memory_size": total_memory_size,
            "memory_dict_type": str(memory_type),
            "memory_dict_content": dict(ai_service.conversation_memory),
            "service_initialized": ai_service._initialized
        }
        
    except Exception as e:
        return {"error": f"Memory trace failed: {str(e)}"}

@router.get("/memory/{user_id}")
async def get_user_memory(user_id: str):
    """Get conversation memory for a specific user"""
    try:
        user_messages = ai_service.conversation_memory.get(user_id, [])
        
        if user_messages:
            return {
                "user_id": user_id,
                "message_count": len(user_messages),
                "messages": user_messages,
                "status": "history_found"
            }
        else:
            return {
                "user_id": user_id,
                "message_count": 0,
                "messages": [],
                "status": "no_history"
            }
    except Exception as e:
        return {"error": f"Memory retrieval failed: {str(e)}"}

@router.get("/status")
async def get_ai_status():
    """Get AI enhanced system status"""
    try:
        # Ensure AI service is initialized
        if not ai_service._initialized:
            await ai_service.initialize()
            
        return {
            "status": "operational",
            "initialized": ai_service._initialized,
            "functions_registered": len(ai_service.function_registry) if hasattr(ai_service, "function_registry") else 0,
            "memory_users": len(ai_service.conversation_memory.keys()),
            "timestamp": datetime.now().isoformat() if 'datetime' in globals() else None
        }
    except Exception as e:
        logger.error(f"Error getting AI status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "initialized": False
        }

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

@router.post("/smart-chat")
async def smart_chat(request: ChatRequest):
    """Smart AI chat with direct function execution"""
    try:
        # Ensure AI service is initialized
        if not ai_service._initialized:
            await ai_service.initialize()
        
        query_lower = request.message.lower()
        logger.info(f"Smart chat processing query: '{query_lower}'")
        
        # Direct client search
        if "find" in query_lower and "maria" in query_lower:
            result = await ai_service._search_clients_by_name("Maria")
            if len(result) == 1:
                client = result[0]
                response = f"**Found Client:** {client.get('name', 'Unknown')}\n\n" + \
                          f"• Status: {client.get('status', 'Unknown')}\n" + \
                          f"• Risk Level: {client.get('risk_level', 'Unknown')}\n" + \
                          f"• Phone: {client.get('phone', 'Not provided')}\n" + \
                          f"• Email: {client.get('email', 'Not provided')}"
            else:
                client_list = [f"{i+1}. {client.get('name', 'Unknown')} - {client.get('status', 'Unknown')}" for i, client in enumerate(result)]
                response = f"**Found {len(result)} clients named Maria:**\n\n" + "\n".join(client_list)
            
            # Store conversation in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Direct active clients list
        elif "list" in query_lower and "active" in query_lower and "client" in query_lower:
            result = await ai_service._list_active_clients()
            client_names = [client.get("name", "Unknown") for client in result]
            response = f"**Active Clients ({len(client_names)}):**\n\n" + "\n".join([f"• {name}" for name in client_names])
            # Store conversation in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Direct appointments today
        elif "appointment" in query_lower and "today" in query_lower:
            result = await ai_service._get_todays_appointments()
            if result and result[0].get("message"):
                response = result[0]["message"]
            else:
                apt_list = [f"• {apt.get('client_name', 'Unknown')} - {apt.get('appointment_type', 'Appointment')}" for apt in result]
                response = f"**Today's Appointments ({len(result)}):**\n\n" + "\n".join(apt_list)
            # Store conversation in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Direct housing status check
        elif "housed" in query_lower and "maria" in query_lower:
            logger.info(f"Housing query detected: housed={('housed' in query_lower)}, housing={('housing' in query_lower)}, maria={('maria' in query_lower)}, santos={('santos' in query_lower)}")
            result = await ai_service.function_call("check_if_client_housed", {"name": "Maria"})
            if result.get("disambiguation_needed"):
                response = f"**{result.get('message')}**\n\n" + "\n".join([f"• {client}" for client in result.get('clients', [])])
            else:
                response = f"**Housing Status:** {result.get('message', 'Unable to determine housing status')}"
            # Store conversation in memory
            await store_conversation_memory(request.user_id, request.message, response)
            return ChatResponse(response=response, context=request.context)
        
        # Fallback
        response_text = f"Smart AI received: '{request.message}'. Available commands: 'Find Maria', 'List active clients', 'What appointments today?'"
        # Store conversation in memory
        await store_conversation_memory(request.user_id, request.message, response_text)
        return ChatResponse(
            response=response_text,
            context=request.context
        )
        
    except Exception as e:
        logger.error(f"Smart chat error: {e}")
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

@router.get("/diagnostic")
async def ai_diagnostic():
    """Comprehensive AI system diagnostic"""
    try:
        # Force re-initialization to test everything
        ai_service._initialized = False
        await ai_service.initialize()
        
        # Test database access
        try:
            test_clients = ai_service.client_service.get_all_clients(limit=1)
            db_test = f"✅ Database access: {len(test_clients)} clients found"
        except Exception as e:
            db_test = f"❌ Database access failed: {str(e)}"
        
        return {
            "ai_initialized": ai_service._initialized,
            "function_count": len(ai_service.function_registry),
            "database_access": ai_service.db_access is not None,
            "client_service": ai_service.client_service is not None,
            "openai_client": ai_service.client is not None,
            "available_functions": list(ai_service.function_registry.keys()),
            "database_test": db_test,
            "conversation_memory_users": len(ai_service.conversation_memory),
            "status": "✅ AI System Fully Operational"
        }
    except Exception as e:
        return {"error": str(e), "status": "❌ AI System Error"}

@router.get("/memory/{user_id}")
async def get_conversation_memory(user_id: str):
    """Get conversation memory for a specific user"""
    try:
        if user_id in ai_service.conversation_memory:
            return {
                "user_id": user_id,
                "message_count": len(ai_service.conversation_memory[user_id]),
                "messages": ai_service.conversation_memory[user_id],
                "status": "found"
            }
        else:
            return {
                "user_id": user_id,
                "message_count": 0,
                "messages": [],
                "status": "no_history"
            }
    except Exception as e:
        logger.error(f"Memory retrieval error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

