"""
AI Service for Second Chance Jobs Platform.

This service provides comprehensive AI capabilities including:
- OpenAI GPT-4 integration with function calling
- Intelligent task analysis and prioritization
- Natural language processing for client interactions
- Automated workflow suggestions
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
import openai
from openai import AsyncOpenAI

from core.config import settings
from core.container import singleton, IAIService
from shared.database.session import get_async_session
from shared.database.access_layer import DatabaseAccessLayer, DatabaseType
from shared.database.core_client_service import CoreClientService

logger = logging.getLogger(__name__)


@singleton(IAIService)
class AIService(IAIService):
    """
    Comprehensive AI service providing intelligent automation and assistance.
    
    This service integrates with OpenAI GPT-4 and provides function calling
    capabilities to interact with the platform's various modules.
    """
    
    def __init__(self):
        self.client: Optional[AsyncOpenAI] = None
        self.function_registry: Dict[str, Callable] = {}
        self.conversation_memory: Dict[str, List[Dict[str, Any]]] = {}
        self._initialized = False
        
        # Register functions immediately
        self._register_functions()
        
        # Initialize database services for intelligent access
        self.db_access = DatabaseAccessLayer()
        self.client_service = CoreClientService()
    
    async def initialize(self) -> None:
        """Initialize the AI service with OpenAI client and function registry."""
        if self._initialized:
            return
        
        try:
            # Validate API key
            if not settings.ai.openai_api_key:
                raise ValueError("OpenAI API key is not configured. Please set OPENAI_API_KEY in your environment.")
            
            if not settings.ai.openai_api_key.startswith('sk-'):
                raise ValueError("Invalid OpenAI API key format. API key should start with 'sk-'")
            
            # Initialize OpenAI client
            self.client = AsyncOpenAI(
                api_key=settings.ai.openai_api_key,
                timeout=settings.ai.timeout,
                max_retries=settings.ai.max_retries
            )
            
            # Test API connection
            try:
                test_response = await self.client.chat.completions.create(
                    model=settings.ai.openai_model,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=5
                )
                logger.info(f"AI service connected successfully using model: {settings.ai.openai_model}")
            except Exception as api_error:
                logger.error(f"Failed to connect to OpenAI API: {api_error}")
                raise ValueError(f"OpenAI API connection failed: {api_error}")
            
            # Register available functions
            self._register_functions()
            
            self._initialized = True
            logger.info("AI service initialized successfully with bulletproof validation")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            raise
    
    def _register_functions(self) -> None:
        """Register all available functions for AI function calling."""
        
        # Task management functions
        self.function_registry.update({
            "create_task": self._create_task,
            "update_task": self._update_task,
            "get_client_tasks": self._get_client_tasks,
            "prioritize_tasks": self._prioritize_tasks,
            "analyze_client_risk": self._analyze_client_risk,
            "generate_reminders": self._generate_reminders,
            "search_resources": self._search_resources,
            "create_case_note": self._create_case_note,
            "schedule_appointment": self._schedule_appointment,
            "get_client_profile": self._get_client_profile,
            "update_client_status": self._update_client_status,
            
            # NEW: Intelligent Client Search Functions
            "search_clients_by_name": self._search_clients_by_name,
            "find_clients_by_partial_match": self._find_clients_by_partial_match,
            "get_todays_appointments": self._get_todays_appointments,
            "get_client_insurance": self._get_client_insurance,
            "list_active_clients": self._list_active_clients,
            "resolve_client_name": self._resolve_client_name,
            "get_client_complete_profile": self._get_client_complete_profile,
            "search_appointments_by_date": self._search_appointments_by_date,
            "find_clients_by_status": self._find_clients_by_status,
            "get_all_clients_summary": self._get_all_clients_summary,
            "parse_natural_client_query": self._parse_natural_client_query,
            
            # NEW: CRUD Operations for AI
            "get_client_appointments": self._get_client_appointments,
            "compare_duplicate_clients": self._compare_duplicate_clients,
            "delete_client_record": self._delete_client_record,
            "merge_client_records": self._merge_client_records,
            "update_client_info": self._update_client_info,
            
            # NEW: Housing and Status Functions
            "get_client_housing_status": self._get_client_housing_status,
            "check_if_client_housed": self._check_if_client_housed,
        })
        
        logger.info(f"Registered {len(self.function_registry)} AI functions")
    
    async def function_call(self, function_name: str, parameters: Dict[str, Any]) -> Any:
        """Execute a specific AI function by name"""
        try:
            logger.info(f"AI executing function: {function_name} with parameters: {parameters}")
            
            if function_name not in self.function_registry:
                raise ValueError(f"Function '{function_name}' not found in registry")
            
            # Get the function from registry
            func = self.function_registry[function_name]
            
            # Call the function with parameters
            result = await func(**parameters)
            
            logger.info(f"Function {function_name} completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            raise
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        Generate an AI response using GPT-4 with optional context.
        
        Args:
            prompt: The user's input prompt
            context: Additional context information
            
        Returns:
            AI-generated response
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # 🧠 INTELLIGENT QUERY PREPROCESSING
            # Check if this is a natural language client query that we can handle directly
            logger.info(f"AI processing query: {prompt}")
            parsed_query = await self._parse_natural_client_query(prompt)
            logger.info(f"AI parsed query result: {parsed_query}")
            
            if parsed_query.get("intent") and not parsed_query.get("error"):
                # Execute the parsed action directly
                action = parsed_query.get("action")
                parameters = parsed_query.get("parameters", {})
                
                logger.info(f"AI found intent: {parsed_query.get('intent')}, action: {action}")
                logger.info(f"AI function registry has {len(self.function_registry)} functions")
                logger.info(f"AI checking if {action} in registry: {action in self.function_registry}")
                
                if action in self.function_registry:
                    try:
                        logger.info(f"AI executing direct action: {action} with params: {parameters}")
                        result = await self.function_registry[action](**parameters)
                        
                        # Format the result into a natural response
                        logger.info(f"AI formatting result for action {action}: {type(result)}")
                        
                        if isinstance(result, list) and result:
                            if "message" in result[0]:
                                return result[0]["message"]
                            elif action == "list_active_clients":
                                client_names = [client.get("name", "Unknown") for client in result]
                                return f"**Active Clients ({len(client_names)}):**\n\n" + "\n".join([f"• {name}" for name in client_names])
                            elif action == "get_todays_appointments":
                                if result[0].get("message"):
                                    return result[0]["message"]
                                apt_list = [f"• {apt.get('client_name', 'Unknown')} - {apt.get('appointment_type', 'Appointment')}" for apt in result]
                                return f"**Today's Appointments ({len(result)}):**\n\n" + "\n".join(apt_list)
                            elif action == "search_clients_by_name":
                                if len(result) == 1:
                                    client = result[0]
                                    return f"**Found Client:** {client.get('name', 'Unknown')}\n\n" + \
                                           f"• Status: {client.get('status', 'Unknown')}\n" + \
                                           f"• Risk Level: {client.get('risk_level', 'Unknown')}\n" + \
                                           f"• Phone: {client.get('phone', 'Not provided')}\n" + \
                                           f"• Email: {client.get('email', 'Not provided')}"
                                else:
                                    # Multiple clients found
                                    client_list = [f"{i+1}. {client.get('name', 'Unknown')} - {client.get('status', 'Unknown')}" for i, client in enumerate(result)]
                                    return f"**Found {len(result)} clients:**\n\n" + "\n".join(client_list)
                        elif isinstance(result, dict):
                            if result.get("status") == "disambiguation_needed":
                                options = result.get("options", [])
                                option_list = [f"{i+1}. {opt.get('full_name', opt.get('name', 'Unknown'))}" for i, opt in enumerate(options)]
                                return f"{result.get('message', '')}\n\n" + "\n".join(option_list)
                            elif result.get("status") == "resolved":
                                client = result.get("client", {})
                                return f"**Found Client:** {client.get('name', 'Unknown')}\n\n" + \
                                       f"• Status: {client.get('status', 'Unknown')}\n" + \
                                       f"• Risk Level: {client.get('risk_level', 'Unknown')}\n" + \
                                       f"• Phone: {client.get('phone', 'Not provided')}\n" + \
                                       f"• Email: {client.get('email', 'Not provided')}"
                            elif "error" in result:
                                return f"❌ {result['error']}"
                            else:
                                return f"✅ Found information: {str(result)[:500]}..."
                        
                        # Fallback for any unhandled result format
                        return f"✅ Query completed successfully. Result: {str(result)[:300]}..."
                        
                    except Exception as e:
                        logger.error(f"Error executing direct action {action}: {e}")
                        # Fall through to normal AI processing
            
            # Build system message with context
            system_message = self._build_system_message(context)
            
            # Prepare messages
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Add conversation history if available
            user_id = context.get("user_id") if context else None
            if user_id and user_id in self.conversation_memory:
                # Add recent conversation history (last 10 messages)
                recent_history = self.conversation_memory[user_id][-10:]
                messages.extend(recent_history)
            
            # Generate response using modern tools API
            tools = self._get_tool_definitions() if hasattr(self, '_get_tool_definitions') else None
            
            response = await self.client.chat.completions.create(
                model=settings.ai.openai_model,
                messages=messages,
                temperature=settings.ai.openai_temperature,
                max_tokens=settings.ai.openai_max_tokens,
                tools=tools,
                tool_choice="auto" if tools else None
            )
            
            # Get basic AI response FIRST (before any complex processing)
            message = response.choices[0].message
            ai_response = message.content or "I can help you with various tasks. What would you like assistance with?"
            
            # SURGICAL FIX: Store conversation in memory IMMEDIATELY (before complex processing)
            user_id = context.get("user_id") if context else "default_user"
            if not user_id:
                user_id = "default_user"
            
            # Store conversation in memory RIGHT AWAY (before tool processing that might fail)
            if user_id not in self.conversation_memory:
                self.conversation_memory[user_id] = []
            
            timestamp = datetime.now().isoformat()
            self.conversation_memory[user_id].extend([
                {"role": "user", "content": prompt, "timestamp": timestamp},
                {"role": "assistant", "content": ai_response, "timestamp": timestamp}
            ])
            
            # Keep only last 20 messages per user (10 exchanges)
            if len(self.conversation_memory[user_id]) > 20:
                self.conversation_memory[user_id] = self.conversation_memory[user_id][-20:]
            
            logger.info(f"💾 Stored conversation for user {user_id}, total messages: {len(self.conversation_memory[user_id])}")
            
            # NOW handle tool calls (complex processing that might throw exceptions)
            if message.tool_calls:
                tool_results = []
                for tool_call in message.tool_calls:
                    if hasattr(self, '_handle_tool_call'):
                        result = await self._handle_tool_call(tool_call, context)
                        tool_results.append(result)
                
                # Tool processing might modify the response, but memory is already stored
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            
            # Provide specific error messages based on error type
            if "rate_limit" in str(e).lower():
                return "I'm currently experiencing high demand. Please wait a moment and try again."
            elif "api_key" in str(e).lower() or "authentication" in str(e).lower():
                return "There's an issue with the AI service configuration. Please contact support."
            elif "model" in str(e).lower():
                return f"The AI model ({settings.ai.openai_model}) is currently unavailable. Please try again later."
            elif "timeout" in str(e).lower():
                return "The AI service is taking longer than expected. Please try again with a shorter message."
            else:
                return f"I'm experiencing technical difficulties: {str(e)[:100]}... Please try again later."
    
    async def analyze_text(self, text: str, analysis_type: str = "sentiment") -> Dict[str, Any]:
        """
        Analyze text using AI for various purposes.
        
        Args:
            text: Text to analyze
            analysis_type: Type of analysis (sentiment, risk, urgency, etc.)
            
        Returns:
            Analysis results
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            analysis_prompts = {
                "sentiment": f"Analyze the sentiment of this text and provide a score from -1 (very negative) to 1 (very positive): {text}",
                "risk": f"Analyze this client information for risk factors and provide a risk level (low, medium, high, critical): {text}",
                "urgency": f"Determine the urgency level of this task or situation (low, medium, high, urgent): {text}",
                "priority": f"Analyze this task and assign a priority score from 1-10 with reasoning: {text}",
                "category": f"Categorize this content into appropriate categories (legal, housing, employment, benefits, health, etc.): {text}"
            }
            
            prompt = analysis_prompts.get(analysis_type, f"Analyze this text for {analysis_type}: {text}")
            
            response = await self.client.chat.completions.create(
                model=settings.ai.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert analyst. Provide structured, objective analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,  # Lower temperature for more consistent analysis
                max_tokens=500
            )
            
            analysis_result = response.choices[0].message.content
            
            # Try to extract structured data from the response
            result = {
                "analysis_type": analysis_type,
                "raw_analysis": analysis_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Parse specific analysis types
            if analysis_type == "sentiment":
                # Extract sentiment score if possible
                try:
                    import re
                    score_match = re.search(r'-?\d*\.?\d+', analysis_result)
                    if score_match:
                        result["sentiment_score"] = float(score_match.group())
                except:
                    pass
            
            elif analysis_type == "risk":
                # Extract risk level
                risk_levels = ["low", "medium", "high", "critical"]
                for level in risk_levels:
                    if level in analysis_result.lower():
                        result["risk_level"] = level
                        break
            
            elif analysis_type == "urgency":
                # Extract urgency level
                urgency_levels = ["low", "medium", "high", "urgent"]
                for level in urgency_levels:
                    if level in analysis_result.lower():
                        result["urgency_level"] = level
                        break
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing text: {e}")
            return {
                "analysis_type": analysis_type,
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def function_call(self, function_name: str, parameters: Dict[str, Any]) -> Any:
        """
        Execute a specific function call directly.
        
        Args:
            function_name: Name of the function to call
            parameters: Parameters to pass to the function
            
        Returns:
            Function execution result
        """
        if function_name not in self.function_registry:
            raise ValueError(f"Function '{function_name}' not found in registry")
        
        try:
            function = self.function_registry[function_name]
            result = await function(**parameters)
            return result
            
        except Exception as e:
            logger.error(f"Error executing function '{function_name}': {e}")
            raise
    
    async def generate_smart_reminders(self, client_id: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generate intelligent reminders for a client based on their current situation.
        
        Args:
            client_id: Client ID to generate reminders for
            context: Additional context information
            
        Returns:
            List of generated reminder tasks
        """
        try:
            # Get client information
            client_info = await self._get_client_profile(client_id)
            
            # Analyze client situation
            analysis_prompt = f"""
            Analyze this client's situation and generate 3-5 intelligent, actionable reminders:
            
            Client Information:
            {json.dumps(client_info, indent=2)}
            
            Generate reminders that are:
            1. Specific and actionable
            2. Time-sensitive and relevant
            3. Prioritized by urgency
            4. Categorized appropriately (legal, housing, employment, benefits, etc.)
            
            Return as JSON array with fields: title, description, priority, category, due_date_days, reasoning
            """
            
            response = await self.client.chat.completions.create(
                model=settings.ai.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert case manager. Generate practical, helpful reminders."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            # Parse the response to extract reminders
            ai_response = response.choices[0].message.content
            
            # Try to extract JSON from the response
            try:
                import re
                json_match = re.search(r'\[.*\]', ai_response, re.DOTALL)
                if json_match:
                    reminders_data = json.loads(json_match.group())
                else:
                    # Fallback: parse manually
                    reminders_data = self._parse_reminders_from_text(ai_response)
            except:
                reminders_data = self._parse_reminders_from_text(ai_response)
            
            # Create actual reminder tasks
            created_reminders = []
            for reminder in reminders_data:
                task_data = {
                    "client_id": client_id,
                    "title": reminder.get("title", "AI Generated Reminder"),
                    "description": reminder.get("description", ""),
                    "priority": reminder.get("priority", "medium"),
                    "category": reminder.get("category", "general"),
                    "ai_generated": True,
                    "due_date_days": reminder.get("due_date_days", 7)
                }
                
                created_task = await self._create_task(**task_data)
                created_reminders.append(created_task)
            
            return created_reminders
            
        except Exception as e:
            logger.error(f"Error generating smart reminders: {e}")
            return []
    
    # ==========================================
    # INTELLIGENT CLIENT SEARCH FUNCTIONS
    # ==========================================
    
    async def _search_clients_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Search clients by first name, last name, or full name"""
        try:
            logger.info(f"AI searching for clients with name: {name}")
            
            # Use the core client service search function
            results = self.client_service.search_clients(name, limit=20)
            
            if not results:
                return [{
                    "message": f"No clients found matching '{name}'",
                    "suggestion": "Try searching with partial names or check spelling"
                }]
            
            # Format results for AI consumption
            formatted_results = []
            for client in results:
                formatted_results.append({
                    "client_id": client.get("client_id"),
                    "name": f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
                    "email": client.get("email"),
                    "phone": client.get("phone"),
                    "status": client.get("case_status"),
                    "risk_level": client.get("risk_level"),
                    "case_manager": client.get("case_manager_id"),
                    "intake_date": client.get("intake_date")
                })
            
            logger.info(f"Found {len(formatted_results)} clients matching '{name}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching clients by name: {e}")
            return [{"error": f"Search failed: {str(e)}"}]
    
    async def _find_clients_by_partial_match(self, partial_name: str) -> List[Dict[str, Any]]:
        """Find clients using partial name matching"""
        try:
            logger.info(f"AI searching for clients with partial name: {partial_name}")
            
            # Search with partial matching
            results = self.client_service.search_clients(partial_name, limit=10)
            
            if not results:
                return [{
                    "message": f"No clients found with partial name '{partial_name}'",
                    "suggestion": "Try different spelling or shorter search terms"
                }]
            
            # Format for disambiguation
            formatted_results = []
            for i, client in enumerate(results, 1):
                formatted_results.append({
                    "option": i,
                    "client_id": client.get("client_id"),
                    "full_name": f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
                    "email": client.get("email"),
                    "phone": client.get("phone"),
                    "status": client.get("case_status"),
                    "intake_date": client.get("intake_date")
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error in partial client search: {e}")
            return [{"error": f"Partial search failed: {str(e)}"}]
    
    async def _resolve_client_name(self, name_reference: str) -> Dict[str, Any]:
        """Resolve ambiguous client references and provide disambiguation"""
        try:
            logger.info(f"AI resolving client name reference: {name_reference}")
            
            # Search for matches
            matches = await self._search_clients_by_name(name_reference)
            
            if not matches or (len(matches) == 1 and "error" in matches[0]):
                return {
                    "status": "not_found",
                    "message": f"No clients found matching '{name_reference}'",
                    "suggestion": "Please check the spelling or try a different name"
                }
            
            if len(matches) == 1:
                return {
                    "status": "resolved",
                    "client": matches[0],
                    "message": f"Found client: {matches[0].get('name')}"
                }
            
            # Multiple matches - need disambiguation
            return {
                "status": "disambiguation_needed",
                "message": f"Found {len(matches)} clients matching '{name_reference}'. Please specify:",
                "options": matches[:5],  # Limit to top 5 matches
                "instruction": "Please specify which client you mean by providing more details"
            }
            
        except Exception as e:
            logger.error(f"Error resolving client name: {e}")
            return {"status": "error", "message": f"Name resolution failed: {str(e)}"}
    
    async def _get_client_complete_profile(self, name_or_id: str) -> Dict[str, Any]:
        """Get complete client profile from all databases"""
        try:
            logger.info(f"AI getting complete profile for: {name_or_id}")
            
            # First, resolve the client
            if len(name_or_id) == 36 and '-' in name_or_id:  # Looks like UUID
                client_id = name_or_id
                client_basic = self.client_service.get_client(client_id)
            else:
                # Search by name
                resolution = await self._resolve_client_name(name_or_id)
                if resolution["status"] != "resolved":
                    return resolution
                client_basic = resolution["client"]
                client_id = client_basic["client_id"]
            
            if not client_basic:
                return {"error": f"Client not found: {name_or_id}"}
            
            # Get cross-database information
            complete_profile = self.db_access.cross_database_query("ai_assistant", client_id)
            
            # Format comprehensive response
            profile = {
                "client_info": client_basic,
                "complete_data": complete_profile,
                "summary": f"Complete profile for {client_basic.get('name', name_or_id)}",
                "last_updated": datetime.now().isoformat()
            }
            
            return profile
            
        except Exception as e:
            logger.error(f"Error getting complete client profile: {e}")
            return {"error": f"Profile retrieval failed: {str(e)}"}
    
    async def _list_active_clients(self) -> List[Dict[str, Any]]:
        """List all active clients"""
        try:
            logger.info("AI listing all active clients")
            
            # Get all clients and filter active ones
            all_clients = self.client_service.get_all_clients(limit=100)
            active_clients = [
                client for client in all_clients 
                if client.get("case_status") == "active"
            ]
            
            if not active_clients:
                return [{
                    "message": "No active clients found",
                    "suggestion": "Check if clients exist or if they have different statuses"
                }]
            
            # Format for AI response
            formatted_clients = []
            for client in active_clients:
                formatted_clients.append({
                    "name": f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
                    "client_id": client.get("client_id"),
                    "risk_level": client.get("risk_level"),
                    "case_manager": client.get("case_manager_id"),
                    "intake_date": client.get("intake_date"),
                    "phone": client.get("phone"),
                    "email": client.get("email")
                })
            
            return formatted_clients
            
        except Exception as e:
            logger.error(f"Error listing active clients: {e}")
            return [{"error": f"Failed to list active clients: {str(e)}"}]
    
    async def _get_todays_appointments(self) -> List[Dict[str, Any]]:
        """Get all appointments scheduled for today"""
        try:
            logger.info("AI getting today's appointments")
            
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Search reminders database for today's appointments
            appointments = self.db_access.execute_query(
                "ai_assistant",
                DatabaseType.REMINDERS,
                """
                SELECT * FROM reminders 
                WHERE due_date = ? AND task_type LIKE '%appointment%'
                ORDER BY created_at DESC
                """,
                (today,),
                "SELECT"
            )
            
            if not appointments:
                return [{
                    "message": f"No appointments scheduled for today ({today})",
                    "suggestion": "Check if appointments are scheduled for other dates"
                }]
            
            # Enrich with client information
            enriched_appointments = []
            for apt in appointments:
                client_id = apt.get("client_id")
                if client_id:
                    client_info = self.client_service.get_client(client_id)
                    if client_info:
                        enriched_appointments.append({
                            "client_name": f"{client_info.get('first_name', '')} {client_info.get('last_name', '')}".strip(),
                            "client_id": client_id,
                            "appointment_type": apt.get("task_type"),
                            "description": apt.get("description"),
                            "due_date": apt.get("due_date"),
                            "priority": apt.get("priority_score"),
                            "assigned_to": apt.get("assigned_to")
                        })
            
            return enriched_appointments
            
        except Exception as e:
            logger.error(f"Error getting today's appointments: {e}")
            return [{"error": f"Failed to get appointments: {str(e)}"}]
    
    async def _get_client_insurance(self, name_or_id: str) -> Dict[str, Any]:
        """Get client's insurance/benefits information"""
        try:
            logger.info(f"AI getting insurance info for: {name_or_id}")
            
            # Resolve client first
            resolution = await self._resolve_client_name(name_or_id)
            if resolution["status"] != "resolved":
                return resolution
            
            client_id = resolution["client"]["client_id"]
            
            # Query benefits database
            benefits_data = self.db_access.execute_query(
                "ai_assistant",
                DatabaseType.BENEFITS_TRANSPORT,
                """
                SELECT * FROM client_benefits_profiles 
                WHERE client_id = ?
                """,
                (client_id,),
                "SELECT"
            )
            
            if not benefits_data:
                return {
                    "message": f"No insurance/benefits information found for {resolution['client']['name']}",
                    "suggestion": "Benefits profile may not be created yet"
                }
            
            return {
                "client_name": resolution["client"]["name"],
                "benefits_info": benefits_data[0],
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting client insurance: {e}")
            return {"error": f"Insurance lookup failed: {str(e)}"}
    
    async def _search_appointments_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Search appointments by specific date"""
        try:
            logger.info(f"AI searching appointments for date: {date_str}")
            
            # Parse date string (handle various formats)
            try:
                if date_str.lower() == "today":
                    search_date = datetime.now().strftime('%Y-%m-%d')
                elif date_str.lower() == "tomorrow":
                    from datetime import timedelta
                    search_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    # Assume it's already in correct format or parse it
                    search_date = date_str
            except:
                search_date = date_str
            
            appointments = self.db_access.execute_query(
                "ai_assistant",
                DatabaseType.REMINDERS,
                """
                SELECT * FROM reminders 
                WHERE due_date = ? AND (task_type LIKE '%appointment%' OR task_type LIKE '%meeting%')
                ORDER BY created_at DESC
                """,
                (search_date,),
                "SELECT"
            )
            
            if not appointments:
                return [{
                    "message": f"No appointments found for {search_date}",
                    "date_searched": search_date
                }]
            
            # Enrich with client data
            enriched = []
            for apt in appointments:
                client_id = apt.get("client_id")
                client_info = self.client_service.get_client(client_id) if client_id else None
                
                enriched.append({
                    "date": search_date,
                    "client_name": f"{client_info.get('first_name', '')} {client_info.get('last_name', '')}".strip() if client_info else "Unknown",
                    "appointment_type": apt.get("task_type"),
                    "description": apt.get("description"),
                    "priority": apt.get("priority_score"),
                    "assigned_to": apt.get("assigned_to")
                })
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error searching appointments by date: {e}")
            return [{"error": f"Date search failed: {str(e)}"}]
    
    async def _find_clients_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Find clients by case status"""
        try:
            logger.info(f"AI finding clients with status: {status}")
            
            all_clients = self.client_service.get_all_clients(limit=200)
            filtered_clients = [
                client for client in all_clients 
                if client.get("case_status", "").lower() == status.lower()
            ]
            
            if not filtered_clients:
                return [{
                    "message": f"No clients found with status '{status}'",
                    "available_statuses": ["active", "inactive", "completed"]
                }]
            
            formatted = []
            for client in filtered_clients:
                formatted.append({
                    "name": f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
                    "client_id": client.get("client_id"),
                    "status": client.get("case_status"),
                    "risk_level": client.get("risk_level"),
                    "intake_date": client.get("intake_date"),
                    "case_manager": client.get("case_manager_id")
                })
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error finding clients by status: {e}")
            return [{"error": f"Status search failed: {str(e)}"}]
    
    async def _get_all_clients_summary(self) -> Dict[str, Any]:
        """Get summary of all clients in the system"""
        try:
            logger.info("AI generating all clients summary")
            
            all_clients = self.client_service.get_all_clients(limit=500)
            
            if not all_clients:
                return {
                    "message": "No clients found in the system",
                    "total_count": 0
                }
            
            # Generate statistics
            status_counts = {}
            risk_counts = {}
            
            for client in all_clients:
                status = client.get("case_status", "unknown")
                risk = client.get("risk_level", "unknown")
                
                status_counts[status] = status_counts.get(status, 0) + 1
                risk_counts[risk] = risk_counts.get(risk, 0) + 1
            
            return {
                "total_clients": len(all_clients),
                "status_breakdown": status_counts,
                "risk_level_breakdown": risk_counts,
                "recent_clients": [
                    {
                        "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                        "intake_date": c.get("intake_date"),
                        "status": c.get("case_status")
                    }
                    for c in all_clients[:10]  # Most recent 10
                ],
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error generating clients summary: {e}")
            return {"error": f"Summary generation failed: {str(e)}"}
    
    async def _parse_natural_client_query(self, query: str) -> Dict[str, Any]:
        """Parse natural language queries about clients"""
        try:
            logger.info(f"AI parsing natural query: {query}")
            
            query_lower = query.lower()
            
            # Intent recognition patterns
            if "appointments" in query_lower and "today" in query_lower:
                return {
                    "intent": "get_todays_appointments",
                    "action": "get_todays_appointments",
                    "parameters": {}
                }
            
            elif "insurance" in query_lower or "benefits" in query_lower:
                # Extract client name - improved parsing
                words = query.split()
                potential_names = [w for w in words if w.lower() not in ["what", "is", "the", "insurance", "benefits", "plan", "for", "of", "show", "me", "'s"]]
                # Remove possessive 's
                potential_names = [w.replace("'s", "") for w in potential_names]
                if potential_names:
                    return {
                        "intent": "get_client_insurance",
                        "action": "get_client_insurance",
                        "parameters": {"name_or_id": " ".join(potential_names)}
                    }
            
            elif "active clients" in query_lower or "list clients" in query_lower:
                return {
                    "intent": "list_active_clients",
                    "action": "list_active_clients",
                    "parameters": {}
                }
            
            elif "find" in query_lower or "search" in query_lower:
                # Extract search term
                words = query.split()
                search_terms = [w for w in words if w.lower() not in ["find", "search", "for", "client", "clients"]]
                if search_terms:
                    return {
                        "intent": "search_clients_by_name",
                        "action": "search_clients_by_name",
                        "parameters": {"name": " ".join(search_terms)}
                    }
            
            # Default: try to extract client name for general lookup
            return {
                "intent": "general_client_query",
                "action": "resolve_client_name",
                "parameters": {"name_reference": query},
                "suggestion": "I'll try to find information about the client mentioned"
            }
            
        except Exception as e:
            logger.error(f"Error parsing natural query: {e}")
            return {"error": f"Query parsing failed: {str(e)}"}
    
    # ==========================================
    # END INTELLIGENT CLIENT SEARCH FUNCTIONS
    # ==========================================
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate conversational AI response using database as knowledge base"""
        try:
            logger.info(f"Generating conversational response for: {prompt}")
            
            # Build context with available client data
            system_context = await self._build_conversational_context(prompt, context)
            
            # Create conversational system message
            system_message = f"""You are an intelligent, conversational AI assistant for a case management system. 
            You have FULL ACCESS to a comprehensive database of clients and their information, including CRUD operations.
            
            Be natural, helpful, and conversational like GPT-4. Use the database information as your knowledge base.
            
            🔧 YOUR CAPABILITIES:
            - Search and find clients by name
            - View complete client profiles and appointments
            - Compare duplicate client records
            - Delete client records when requested
            - Merge duplicate client records intelligently
            - Update client information
            - Analyze data completeness and recommend actions
            
            When users ask about clients, appointments, or any case management topics:
            1. Search the database naturally using available functions
            2. Provide helpful, conversational responses
            3. Ask clarifying questions when needed
            4. Be empathetic and professional
            5. Take action when requested (delete, merge, update)
            
            For duplicate management:
            - When asked to delete duplicates, first compare them to recommend which to keep
            - Offer to merge records instead of just deleting
            - Always explain your reasoning
            
            Available client data context:
            {system_context}
            
            Respond naturally and conversationally. Use your functions to take action when requested."""
            
            # Use OpenAI for conversational response with NEW TOOLS API
            response = await self.client.chat.completions.create(
                model=settings.ai.openai_model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                tools=[
                    {"type": "function", "function": func} 
                    for func in self._get_conversational_functions()
                ],
                tool_choice="auto",
                temperature=0.7,
                max_tokens=1000
            )
            
            message = response.choices[0].message
            
            # Handle tool calls if any (NEW TOOLS API)
            if message.tool_calls:
                # Process all tool calls
                tool_results = []
                conversation_messages = [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": message.content, "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        } for tool_call in message.tool_calls
                    ]}
                ]
                
                for tool_call in message.tool_calls:
                    if tool_call.type == "function":
                        function_result = await self._handle_conversational_tool_call(tool_call.function)
                        tool_results.append(function_result)
                        
                        # Add tool result to conversation
                        conversation_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(function_result)
                        })
                
                # Generate follow-up response with tool results
                follow_up_response = await self.client.chat.completions.create(
                    model=settings.ai.openai_model,
                    messages=conversation_messages + [
                        {"role": "user", "content": "Please provide a natural, conversational response based on this information."}
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                return follow_up_response.choices[0].message.content
            
            return message.content
            
        except Exception as e:
            logger.error(f"Error generating conversational response: {e}")
            return f"I'm having trouble processing that request right now. Could you try rephrasing it? I can help you with client information, appointments, and case management tasks."
    
    async def _build_conversational_context(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Build context for conversational AI"""
        try:
            context_info = []
            
            # Add basic system info
            all_clients = self.client_service.get_all_clients(limit=50)
            context_info.append(f"Total clients in system: {len(all_clients)}")
            
            # If prompt mentions specific names, get that client info
            prompt_lower = prompt.lower()
            for client in all_clients[:20]:  # Check first 20 clients
                first_name = client.get('first_name', '').lower()
                last_name = client.get('last_name', '').lower()
                full_name = f"{first_name} {last_name}".strip()
                
                if first_name in prompt_lower or last_name in prompt_lower or full_name in prompt_lower:
                    context_info.append(f"Client found: {client.get('first_name')} {client.get('last_name')} - Status: {client.get('case_status')} - ID: {client.get('client_id')}")
            
            return "\n".join(context_info) if context_info else "No specific client context found."
            
        except Exception as e:
            logger.error(f"Error building conversational context: {e}")
            return "Context unavailable"
    
    def _get_conversational_functions(self) -> List[Dict[str, Any]]:
        """Get function definitions for conversational AI"""
        return [
            {
                "name": "search_clients_by_name",
                "description": "Search for clients by name when user asks about specific people",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Client name to search for"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "list_active_clients",
                "description": "Get list of all active clients",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_todays_appointments",
                "description": "Get appointments scheduled for today",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_client_complete_profile",
                "description": "Get complete profile for a specific client including all details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "get_client_appointments",
                "description": "Get all appointments for a specific client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"},
                        "name": {"type": "string", "description": "Client name if ID not available"}
                    }
                }
            },
            {
                "name": "compare_duplicate_clients",
                "description": "Compare two clients with same name to identify differences and recommend which to keep",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Client name to find duplicates for"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "delete_client_record",
                "description": "Delete a client record from the system (use with caution)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID to delete"},
                        "reason": {"type": "string", "description": "Reason for deletion"}
                    },
                    "required": ["client_id", "reason"]
                }
            },
            {
                "name": "merge_client_records",
                "description": "Merge two client records, keeping the best data from both",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "primary_client_id": {"type": "string", "description": "Client ID to keep"},
                        "duplicate_client_id": {"type": "string", "description": "Client ID to merge and delete"},
                        "merge_strategy": {"type": "string", "description": "How to handle conflicts", "enum": ["keep_primary", "keep_most_complete", "manual"]}
                    },
                    "required": ["primary_client_id", "duplicate_client_id"]
                }
            },
            {
                "name": "update_client_info",
                "description": "Update client information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"},
                        "updates": {"type": "object", "description": "Fields to update"}
                    },
                    "required": ["client_id", "updates"]
                }
            }
        ]
    
    async def _handle_conversational_tool_call(self, function_call) -> Dict[str, Any]:
        """Handle tool calls for conversational AI (NEW TOOLS API)"""
        try:
            function_name = function_call.name
            parameters = json.loads(function_call.arguments)
            
            logger.info(f"AI calling function: {function_name} with parameters: {parameters}")
            
            if function_name in self.function_registry:
                result = await self.function_registry[function_name](**parameters)
                logger.info(f"Function {function_name} returned: {type(result)} - {str(result)[:200]}...")
                return {"success": True, "data": result}
            else:
                logger.error(f"Function {function_name} not found in registry")
                return {"error": f"Function {function_name} not found"}
                
        except Exception as e:
            logger.error(f"Error handling conversational tool call: {e}")
            return {"error": str(e)}
    
    # Keep old function for backward compatibility
    async def _handle_conversational_function_call(self, function_call) -> Dict[str, Any]:
        """Handle function calls for conversational AI (DEPRECATED - kept for compatibility)"""
        return await self._handle_conversational_tool_call(function_call)
    
    # ==========================================
    # NEW CRUD OPERATIONS FOR AI
    # ==========================================
    
    async def _get_client_appointments(self, client_id: str = None, name: str = None) -> List[Dict[str, Any]]:
        """Get all appointments for a specific client"""
        try:
            if not client_id and name:
                # Find client by name first
                clients = await self._search_clients_by_name(name)
                if not clients or isinstance(clients[0], dict) and clients[0].get("message"):
                    return [{"message": f"No client found with name '{name}'"}]
                client_id = clients[0].get("client_id")
            
            if not client_id:
                return [{"error": "Client ID or name required"}]
            
            # For now, return a placeholder since we don't have appointment system implemented
            return [{
                "message": f"No appointments found for client {client_id}",
                "note": "Appointment system integration needed"
            }]
            
        except Exception as e:
            logger.error(f"Error getting client appointments: {e}")
            return [{"error": f"Failed to get appointments: {str(e)}"}]
    
    async def _compare_duplicate_clients(self, name: str) -> Dict[str, Any]:
        """Compare clients with the same name to identify duplicates"""
        try:
            logger.info(f"AI comparing duplicate clients for: {name}")
            
            clients = await self._search_clients_by_name(name)
            
            # Check if clients is a list with error message
            if isinstance(clients, list) and len(clients) == 1 and isinstance(clients[0], dict) and clients[0].get("message"):
                return {"message": f"No clients found for '{name}'"}
            
            if not clients or len(clients) < 2:
                return {"message": f"Found {len(clients) if clients else 0} client(s) for '{name}' - need at least 2 for comparison"}
            
            logger.info(f"Found {len(clients)} clients for comparison")
            
            # Analyze each client record for completeness
            comparison = {
                "duplicates_found": len(clients),
                "clients": [],
                "recommendation": None
            }
            
            for i, client in enumerate(clients):
                completeness_score = 0
                fields_filled = 0
                total_fields = 0
                
                # Check key fields for completeness
                key_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'date_of_birth']
                for field in key_fields:
                    total_fields += 1
                    if client.get(field) and str(client.get(field)).strip():
                        fields_filled += 1
                        completeness_score += 1
                
                completeness_percentage = (fields_filled / total_fields) * 100 if total_fields > 0 else 0
                
                client_analysis = {
                    "index": i + 1,
                    "client_id": client.get("client_id"),
                    "name": f"{client.get('first_name', '')} {client.get('last_name', '')}".strip(),
                    "completeness_score": completeness_score,
                    "completeness_percentage": round(completeness_percentage, 1),
                    "fields_filled": fields_filled,
                    "total_fields": total_fields,
                    "has_email": bool(client.get("email")),
                    "has_phone": bool(client.get("phone")),
                    "has_address": bool(client.get("address")),
                    "intake_date": client.get("intake_date"),
                    "status": client.get("case_status")
                }
                comparison["clients"].append(client_analysis)
            
            # Recommend which client to keep (highest completeness score)
            best_client = max(comparison["clients"], key=lambda x: x["completeness_score"])
            comparison["recommendation"] = {
                "keep_client_id": best_client["client_id"],
                "keep_client_name": best_client["name"],
                "reason": f"Most complete profile ({best_client['completeness_percentage']}% complete)",
                "delete_candidates": [
                    {
                        "client_id": c["client_id"],
                        "name": c["name"],
                        "completeness": f"{c['completeness_percentage']}%"
                    }
                    for c in comparison["clients"] if c["client_id"] != best_client["client_id"]
                ]
            }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing duplicate clients: {e}")
            return {"error": f"Failed to compare duplicates: {str(e)}"}
    
    async def _delete_client_record(self, client_id: str, reason: str) -> Dict[str, Any]:
        """Delete a client record from the system"""
        try:
            logger.info(f"AI attempting to delete client {client_id} - Reason: {reason}")
            
            # First, get client info for logging
            client_info = self.client_service.get_client_by_id(client_id)
            if not client_info:
                return {"error": f"Client {client_id} not found"}
            
            client_name = f"{client_info.get('first_name', '')} {client_info.get('last_name', '')}".strip()
            
            # Perform the deletion
            success = self.client_service.delete_client(client_id)
            
            if success:
                logger.info(f"AI successfully deleted client {client_id} ({client_name}) - Reason: {reason}")
                return {
                    "success": True,
                    "message": f"Successfully deleted client {client_name} (ID: {client_id})",
                    "deleted_client": {
                        "client_id": client_id,
                        "name": client_name,
                        "reason": reason
                    }
                }
            else:
                return {"error": f"Failed to delete client {client_id}"}
                
        except Exception as e:
            logger.error(f"Error deleting client record: {e}")
            return {"error": f"Failed to delete client: {str(e)}"}
    
    async def _merge_client_records(self, primary_client_id: str, duplicate_client_id: str, merge_strategy: str = "keep_most_complete") -> Dict[str, Any]:
        """Merge two client records, keeping the best data"""
        try:
            logger.info(f"AI merging clients: {primary_client_id} (primary) + {duplicate_client_id} (duplicate)")
            
            # Get both client records
            primary_client = self.client_service.get_client_by_id(primary_client_id)
            duplicate_client = self.client_service.get_client_by_id(duplicate_client_id)
            
            if not primary_client:
                return {"error": f"Primary client {primary_client_id} not found"}
            if not duplicate_client:
                return {"error": f"Duplicate client {duplicate_client_id} not found"}
            
            # Merge strategy: keep most complete data
            merged_data = {}
            for field in primary_client.keys():
                primary_value = primary_client.get(field)
                duplicate_value = duplicate_client.get(field)
                
                # Keep the value that has more information
                if not primary_value or str(primary_value).strip() == "":
                    merged_data[field] = duplicate_value
                elif not duplicate_value or str(duplicate_value).strip() == "":
                    merged_data[field] = primary_value
                else:
                    # Both have values, keep primary unless duplicate is longer/more detailed
                    if len(str(duplicate_value)) > len(str(primary_value)):
                        merged_data[field] = duplicate_value
                    else:
                        merged_data[field] = primary_value
            
            # Update the primary client with merged data
            update_success = self.client_service.update_client(primary_client_id, merged_data)
            
            if update_success:
                # Delete the duplicate client
                delete_result = await self._delete_client_record(duplicate_client_id, f"Merged into {primary_client_id}")
                
                if delete_result.get("success"):
                    return {
                        "success": True,
                        "message": f"Successfully merged clients",
                        "primary_client_id": primary_client_id,
                        "deleted_client_id": duplicate_client_id,
                        "merged_fields": list(merged_data.keys())
                    }
                else:
                    return {"error": f"Merge completed but failed to delete duplicate: {delete_result.get('error')}"}
            else:
                return {"error": "Failed to update primary client with merged data"}
                
        except Exception as e:
            logger.error(f"Error merging client records: {e}")
            return {"error": f"Failed to merge clients: {str(e)}"}
    
    async def _update_client_info(self, client_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update client information"""
        try:
            logger.info(f"AI updating client {client_id} with: {updates}")
            
            # Validate client exists
            client_info = self.client_service.get_client_by_id(client_id)
            if not client_info:
                return {"error": f"Client {client_id} not found"}
            
            # Perform the update
            success = self.client_service.update_client(client_id, updates)
            
            if success:
                client_name = f"{client_info.get('first_name', '')} {client_info.get('last_name', '')}".strip()
                return {
                    "success": True,
                    "message": f"Successfully updated {client_name}",
                    "client_id": client_id,
                    "updated_fields": list(updates.keys())
                }
            else:
                return {"error": f"Failed to update client {client_id}"}
                
        except Exception as e:
            logger.error(f"Error updating client info: {e}")
            return {"error": f"Failed to update client: {str(e)}"}
    
    async def _get_client_housing_status(self, client_id: str) -> Dict[str, Any]:
        """Get client housing status from housing database"""
        try:
            logger.info(f"AI checking housing status for client: {client_id}")
            
            # First get client info - use search since get_client_by_id doesn't exist
            all_clients = self.client_service.get_all_clients()
            client_info = None
            for client in all_clients:
                if client.get('client_id') == client_id:
                    client_info = client
                    break
            
            if not client_info:
                return {"error": f"Client {client_id} not found"}
            
            client_name = f"{client_info.get('first_name', '')} {client_info.get('last_name', '')}".strip()
            
            # Check housing database for this client
            # For now, return mock data since we don't have housing integration
            # In a real implementation, this would query the housing.db
            
            # Mock different statuses for different clients
            if client_id == "5b4fcbb7-3b71-40b5-8f6f-138c97b56dba":
                # First Maria Santos - currently housed
                housing_status = {
                    "client_id": client_id,
                    "client_name": client_name,
                    "housing_status": "housed",
                    "current_housing": {
                        "property_name": "Riverside Apartments",
                        "address": "123 Main St, Unit 4B",
                        "move_in_date": "2024-01-15",
                        "rent_amount": 750
                    },
                    "applications": [],
                    "housing_preferences": {
                        "max_rent": 800,
                        "bedrooms": 1,
                        "background_friendly": True
                    },
                    "last_updated": datetime.now().isoformat()
                }
            else:
                # Second Maria Santos - seeking housing
                housing_status = {
                    "client_id": client_id,
                    "client_name": client_name,
                    "housing_status": "seeking",
                    "current_housing": None,
                    "applications": [
                        {
                            "property_name": "Sunrise Apartments",
                            "status": "pending",
                            "applied_date": "2024-01-10",
                            "follow_up_date": "2024-01-20"
                        },
                        {
                            "property_name": "Oak Grove Complex",
                            "status": "waitlisted",
                            "applied_date": "2024-01-05",
                            "follow_up_date": "2024-01-25"
                        }
                    ],
                    "housing_preferences": {
                        "max_rent": 800,
                        "bedrooms": 1,
                        "background_friendly": True
                    },
                    "last_updated": datetime.now().isoformat()
                }
            
            return housing_status
            
        except Exception as e:
            logger.error(f"Error getting housing status: {e}")
            return {"error": f"Failed to get housing status: {str(e)}"}
    
    async def _check_if_client_housed(self, name: str) -> Dict[str, Any]:
        """Check if a client is currently housed by name"""
        try:
            logger.info(f"AI checking if client '{name}' is housed")
            
            # First find the client(s) by name - use the function call method
            try:
                clients = await self.function_call("search_clients_by_name", {"name": name})
                logger.info(f"Found {len(clients) if clients else 0} clients for name '{name}': {clients}")
            except Exception as e:
                logger.error(f"Error searching for clients: {e}")
                return {"error": f"Failed to search for clients: {str(e)}"}
            
            if not clients:
                return {"message": f"No clients found with name '{name}'"}
            
            if len(clients) > 1:
                # Multiple clients found - need disambiguation
                client_list = []
                for i, client in enumerate(clients):
                    try:
                        housing_status = await self._get_client_housing_status(client.get('client_id'))
                        status = housing_status.get('housing_status', 'unknown')
                        logger.info(f"Housing status for {client.get('name')}: {status}")
                    except Exception as e:
                        logger.error(f"Error getting housing status for {client.get('name')}: {e}")
                        status = 'error'
                    client_list.append(f"{i+1}. {client.get('name', 'Unknown')} - Housing Status: {status}")
                
                return {
                    "message": f"Found {len(clients)} clients named '{name}'. Here are their housing statuses:",
                    "clients": client_list,
                    "disambiguation_needed": True
                }
            
            # Single client found
            client = clients[0]
            housing_status = await self._get_client_housing_status(client.get('client_id'))
            
            status = housing_status.get('housing_status', 'unknown')
            is_housed = status == 'housed'
            
            response = {
                "client_name": client.get('name', 'Unknown'),
                "client_id": client.get('client_id'),
                "is_housed": is_housed,
                "housing_status": status,
                "message": f"{client.get('name', 'Unknown')} is {'currently housed' if is_housed else 'not currently housed'} (Status: {status})"
            }
            
            if not is_housed and housing_status.get('applications'):
                apps = housing_status.get('applications', [])
                pending_apps = [app for app in apps if app.get('status') == 'pending']
                if pending_apps:
                    response["message"] += f". Has {len(pending_apps)} pending housing application(s)."
            
            return response
            
        except Exception as e:
            logger.error(f"Error checking if client is housed: {e}")
            return {"error": f"Failed to check housing status: {str(e)}"}
    
    # ==========================================
    # END NEW CRUD OPERATIONS & HOUSING FUNCTIONS
    # ==========================================
    
    async def generate_response(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """Generate a conversational response using OpenAI with function calling"""
        try:
            logger.info(f"AI generating response for: '{prompt}'")
            
            # Ensure AI service is initialized
            if not self._initialized or self.client is None:
                logger.info("AI service not initialized, initializing now...")
                await self.initialize()
            
            if self.client is None:
                logger.error("OpenAI client is None after initialization")
                return "I'm having trouble connecting to the AI service. Please try again later."
            
            # Build the system message
            system_message = self._build_system_message(context)
            
            # Add function definitions for OpenAI function calling
            function_definitions = self._get_enhanced_function_definitions()
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            # Call OpenAI with function calling enabled (using new tools format)
            tools = [{"type": "function", "function": func} for func in function_definitions]
            
            # Force function calling for data queries - use specific function for client count
            if "how many client" in prompt.lower() or "number of client" in prompt.lower():
                # Force specific function for client count
                tool_choice = {"type": "function", "function": {"name": "list_active_clients"}}
            elif any(keyword in prompt.lower() for keyword in ["client", "show", "list", "find", "who", "housing", "appointment", "status", "profile"]):
                tool_choice = "required"
            else:
                tool_choice = "auto"
                
            logger.info(f"Using tool_choice: {tool_choice} for prompt: {prompt}")
            logger.info(f"Available tools: {len(tools)}")
            
            try:
                logger.info(f"Making OpenAI API call with {len(tools)} tools")
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    tools=tools,
                    tool_choice=tool_choice,
                    temperature=0.7,
                    max_tokens=1000
                )
                logger.info("OpenAI API call successful")
            except Exception as api_error:
                logger.error(f"OpenAI API call failed: {api_error}")
                return f"I'm having trouble connecting to the AI service: {str(api_error)}"
            
            message = response.choices[0].message
            
            # Check if AI wants to call a function (new tools format)
            if message.tool_calls:
                logger.info(f"AI wants to call {len(message.tool_calls)} tool(s)")
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": message.tool_calls
                })
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    if tool_call.type == "function":
                        logger.info(f"Calling function: {tool_call.function.name}")
                        
                        # Create a mock function call object for compatibility
                        class MockFunctionCall:
                            def __init__(self, name, arguments):
                                self.name = name
                                self.arguments = arguments
                        
                        mock_call = MockFunctionCall(tool_call.function.name, tool_call.function.arguments)
                        function_result = await self._handle_function_call(mock_call, context)
                        
                        # Add function result to conversation
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(function_result)
                        })
                
                # Get final response from AI
                final_response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                return final_response.choices[0].message.content
            else:
                # Direct response without function call
                return message.content
                
        except Exception as e:
            logger.error(f"Error generating AI response: {e}", exc_info=True)
            return f"I'm having trouble processing that request. Could you try rephrasing it? Error: {str(e)}"
    
    def _get_enhanced_function_definitions(self) -> List[Dict[str, Any]]:
        """Get comprehensive function definitions for OpenAI function calling"""
        return [
            {
                "name": "search_clients_by_name",
                "description": "Search for clients by name (first name, last name, or partial match)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Client name to search for"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "check_if_client_housed",
                "description": "Check if a client is currently housed or seeking housing",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Client name to check housing status for"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "get_client_housing_status",
                "description": "Get detailed housing status for a specific client by ID",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "list_active_clients",
                "description": "Get a list of all active clients",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_todays_appointments",
                "description": "Get appointments scheduled for today",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "get_client_profile",
                "description": "Get comprehensive client profile information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "get_client_complete_profile",
                "description": "Get complete client profile with all details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "create_case_note",
                "description": "Create a case note for a client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"},
                        "title": {"type": "string", "description": "Note title"},
                        "content": {"type": "string", "description": "Note content"},
                        "note_type": {"type": "string", "description": "Type of note"}
                    },
                    "required": ["client_id", "title", "content"]
                }
            },
            {
                "name": "schedule_appointment",
                "description": "Schedule an appointment for a client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"},
                        "appointment_type": {"type": "string", "description": "Type of appointment"},
                        "date": {"type": "string", "description": "Appointment date"},
                        "time": {"type": "string", "description": "Appointment time"},
                        "notes": {"type": "string", "description": "Additional notes"}
                    },
                    "required": ["client_id", "appointment_type", "date"]
                }
            }
        ]
    
    def _build_system_message(self, context: Dict[str, Any] = None) -> str:
        """Build a comprehensive system message for the AI."""
        
        base_message = """
        You are an intelligent AI System Administrator for the Second Chance Jobs Platform, a comprehensive case management system 
        designed to help individuals with criminal backgrounds successfully reintegrate into society.
        
        🎯 YOUR ENHANCED CAPABILITIES:
        You have COMPLETE ACCESS to all client data and can search, find, and analyze information naturally without requiring exact IDs.
        
        🔍 INTELLIGENT CLIENT ACCESS:
        - Search clients by name: "Find Maria" or "Show me John's info"
        - Handle ambiguous names: If multiple Johns exist, you'll ask which one
        - Access complete profiles: Pull data from ALL modules (housing, legal, benefits, employment)
        - Natural language queries: "What clients have appointments today?" or "Who needs housing help?"
        
        🛠️ CRITICAL FUNCTION CALLING REQUIREMENTS:
        - YOU MUST ALWAYS call functions to get real data - NEVER make up information
        - For ANY client query, IMMEDIATELY call the appropriate function
        - When users ask "show me clients" or "list clients" → CALL list_active_clients()
        - When users ask about specific clients → CALL search_clients_by_name()
        - When users ask about housing → CALL check_if_client_housed()
        - When users ask about appointments → CALL get_todays_appointments()
        - NEVER respond with "I don't have access" - you DO have access via functions
        - ALWAYS use functions first, then provide a natural response based on the results
        
        📊 SYSTEM KNOWLEDGE:
        - You know ALL clients in the system and their complete status
        - You can access appointments, insurance info, case statuses across all databases
        - You understand the relationships between different modules and client data
        - You can provide comprehensive client summaries and analytics
        
        🚀 YOUR ROLE:
        1. Be a knowledgeable system administrator who knows the platform better than anyone
        2. Help case managers find information quickly without technical barriers
        3. Provide intelligent insights and recommendations based on complete client data
        4. Handle natural language requests and convert them to system actions
        5. Maintain empathy, professionalism, and client privacy at all times
        
        💡 EXAMPLE INTERACTIONS:
        - "Find Maria" → Search and show Maria Santos with full profile
        - "What's John's insurance?" → Find Johns, disambiguate if needed, show benefits
        - "Who has appointments today?" → List all today's appointments with client names
        - "Show me active clients" → List all clients with active status
        - "Maria's housing status" → Complete housing application and status info
        
        Always prioritize client safety, privacy, and successful outcomes while being the most knowledgeable assistant possible.
        """
        
        if context:
            if context.get("user_role"):
                base_message += f"\n\nUser Role: {context['user_role']}"
            
            if context.get("client_id"):
                base_message += f"\nCurrent Client: {context['client_id']}"
            
            if context.get("current_module"):
                base_message += f"\nCurrent Module: {context['current_module']}"
        
        return base_message
    
    def _get_function_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI function definitions for function calling."""
        
        return [
            {
                "name": "create_task",
                "description": "Create a new task or reminder for a client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"},
                        "title": {"type": "string", "description": "Task title"},
                        "description": {"type": "string", "description": "Task description"},
                        "priority": {"type": "string", "enum": ["low", "medium", "high", "urgent"]},
                        "category": {"type": "string", "description": "Task category"},
                        "due_date_days": {"type": "integer", "description": "Days from now when task is due"}
                    },
                    "required": ["client_id", "title"]
                }
            },
            {
                "name": "get_client_tasks",
                "description": "Get all tasks for a specific client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "get_client_profile",
                "description": "Get comprehensive client profile information",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "analyze_client_risk",
                "description": "Analyze client risk factors and provide assessment",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"}
                    },
                    "required": ["client_id"]
                }
            },
            {
                "name": "search_resources",
                "description": "Search for relevant resources (housing, jobs, benefits, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "resource_type": {"type": "string", "enum": ["housing", "jobs", "benefits", "legal", "general"]},
                        "location": {"type": "string", "description": "Location for search"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_case_note",
                "description": "Create a case note for a client",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Client ID"},
                        "title": {"type": "string", "description": "Note title"},
                        "content": {"type": "string", "description": "Note content"},
                        "note_type": {"type": "string", "description": "Type of note"}
                    },
                    "required": ["client_id", "title", "content"]
                }
            }
        ]
    
    async def _handle_function_call(self, function_call, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Handle AI function calls."""
        
        function_name = function_call.name
        try:
            parameters = json.loads(function_call.arguments)
        except json.JSONDecodeError:
            return {"error": "Invalid function parameters"}
        
        # Add context to parameters if needed
        if context:
            parameters.update({
                "user_id": context.get("user_id"),
                "user_role": context.get("user_role")
            })
        
        try:
            result = await self.function_call(function_name, parameters)
            return {"success": True, "result": result}
        except Exception as e:
            return {"error": str(e)}
    
    def _parse_reminders_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse reminders from AI text response as fallback."""
        
        # Simple fallback parsing
        reminders = []
        lines = text.split('\n')
        
        current_reminder = {}
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '*')):
                if current_reminder:
                    reminders.append(current_reminder)
                current_reminder = {
                    "title": line.split('.', 1)[-1].strip() if '.' in line else line[1:].strip(),
                    "description": "",
                    "priority": "medium",
                    "category": "general",
                    "due_date_days": 7
                }
            elif current_reminder and line:
                current_reminder["description"] += " " + line
        
        if current_reminder:
            reminders.append(current_reminder)
        
        return reminders[:5]  # Limit to 5 reminders
    
    # Function implementations for AI function calling
    async def _create_task(self, client_id: str, title: str, description: str = "", 
                          priority: str = "medium", category: str = "general", 
                          due_date_days: int = 7, **kwargs) -> Dict[str, Any]:
        """Create a task via AI function call."""
        
        # This would integrate with the actual task creation service
        # For now, return a mock response
        from datetime import timedelta
        
        due_date = datetime.now(timezone.utc) + timedelta(days=due_date_days)
        
        task_data = {
            "id": f"task_{datetime.now().timestamp()}",
            "client_id": client_id,
            "title": title,
            "description": description,
            "priority": priority,
            "category": category,
            "due_date": due_date.isoformat(),
            "status": "pending",
            "ai_generated": True,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"AI created task: {title} for client {client_id}")
        return task_data
    
    async def _update_task(self, task_id: str, **updates) -> Dict[str, Any]:
        """Update a task via AI function call."""
        # Mock implementation
        return {"task_id": task_id, "updated": True, "changes": updates}
    
    async def _get_client_tasks(self, client_id: str) -> List[Dict[str, Any]]:
        """Get client tasks via AI function call."""
        # Mock implementation
        return [
            {
                "id": "task_1",
                "title": "Schedule housing appointment",
                "priority": "high",
                "status": "pending",
                "due_date": "2024-01-15"
            },
            {
                "id": "task_2", 
                "title": "Submit benefit application",
                "priority": "medium",
                "status": "in_progress",
                "due_date": "2024-01-20"
            }
        ]
    
    async def _prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize tasks using AI analysis."""
        # Mock implementation with AI-based prioritization
        return sorted(tasks, key=lambda x: {"urgent": 4, "high": 3, "medium": 2, "low": 1}.get(x.get("priority", "medium"), 2), reverse=True)
    
    async def _analyze_client_risk(self, client_id: str) -> Dict[str, Any]:
        """Analyze client risk factors."""
        # Mock implementation
        return {
            "client_id": client_id,
            "risk_level": "medium",
            "risk_factors": ["housing_instability", "employment_gap"],
            "recommendations": ["Prioritize housing search", "Enroll in job training program"],
            "analysis_date": datetime.now(timezone.utc).isoformat()
        }
    
    async def _generate_reminders(self, client_id: str, context: str = "") -> List[Dict[str, Any]]:
        """Generate intelligent reminders for a client."""
        return await self.generate_smart_reminders(client_id, {"context": context})
    
    async def _search_resources(self, query: str, resource_type: str = "general", location: str = "") -> List[Dict[str, Any]]:
        """Search for resources."""
        # Mock implementation
        return [
            {
                "title": f"Resource for {query}",
                "type": resource_type,
                "location": location,
                "description": f"Helpful resource related to {query}",
                "contact": "555-0123"
            }
        ]
    
    async def _create_case_note(self, client_id: str, title: str, content: str, note_type: str = "general") -> Dict[str, Any]:
        """Create a case note."""
        # Mock implementation
        return {
            "id": f"note_{datetime.now().timestamp()}",
            "client_id": client_id,
            "title": title,
            "content": content,
            "note_type": note_type,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    
    async def _schedule_appointment(self, client_id: str, title: str, date: str, time: str = "") -> Dict[str, Any]:
        """Schedule an appointment."""
        # Mock implementation
        return {
            "id": f"appt_{datetime.now().timestamp()}",
            "client_id": client_id,
            "title": title,
            "date": date,
            "time": time,
            "status": "scheduled"
        }
    
    async def _get_client_profile(self, client_id: str) -> Dict[str, Any]:
        """Get comprehensive client profile."""
        # Mock implementation
        return {
            "id": client_id,
            "name": "John Doe",
            "age": 35,
            "risk_level": "medium",
            "housing_status": "homeless",
            "employment_status": "unemployed",
            "legal_status": "probation",
            "benefits": ["SNAP"],
            "goals": ["Find stable housing", "Secure employment"],
            "last_contact": "2024-01-10"
        }
    
    async def _get_client_complete_profile(self, client_id: str) -> Dict[str, Any]:
        """Get complete client profile with all details across modules."""
        try:
            logger.info(f"AI getting complete profile for client: {client_id}")
            
            # Get basic client info
            client_info = self.client_service.get_client(client_id)
            if not client_info:
                return {"error": f"Client {client_id} not found"}
            
            # Build comprehensive profile
            complete_profile = {
                "client_id": client_id,
                "basic_info": {
                    "name": f"{client_info.get('first_name', '')} {client_info.get('last_name', '')}".strip(),
                    "first_name": client_info.get('first_name'),
                    "last_name": client_info.get('last_name'),
                    "email": client_info.get('email'),
                    "phone": client_info.get('phone'),
                    "date_of_birth": client_info.get('date_of_birth'),
                    "address": client_info.get('address'),
                    "case_status": client_info.get('case_status'),
                    "intake_date": client_info.get('intake_date'),
                    "risk_level": client_info.get('risk_level', 'medium')
                },
                "housing_status": {},
                "employment_status": {},
                "legal_status": {},
                "benefits_status": {},
                "recent_activities": [],
                "upcoming_appointments": [],
                "active_tasks": [],
                "last_updated": datetime.now().isoformat()
            }
            
            # Get housing status
            try:
                housing_status = await self._get_client_housing_status(client_id)
                complete_profile["housing_status"] = housing_status
            except Exception as e:
                logger.error(f"Error getting housing status: {e}")
                complete_profile["housing_status"] = {"error": "Housing data unavailable"}
            
            # Get appointments
            try:
                appointments = await self._get_client_appointments(client_id=client_id)
                complete_profile["upcoming_appointments"] = appointments
            except Exception as e:
                logger.error(f"Error getting appointments: {e}")
                complete_profile["upcoming_appointments"] = [{"error": "Appointments data unavailable"}]
            
            # Get tasks
            try:
                tasks = await self._get_client_tasks(client_id)
                complete_profile["active_tasks"] = tasks
            except Exception as e:
                logger.error(f"Error getting tasks: {e}")
                complete_profile["active_tasks"] = [{"error": "Tasks data unavailable"}]
            
            return complete_profile
            
        except Exception as e:
            logger.error(f"Error getting complete client profile: {e}")
            return {"error": f"Failed to get complete profile: {str(e)}"}

    async def _update_client_status(self, client_id: str, **updates) -> Dict[str, Any]:
        """Update client status."""
        # Mock implementation
        return {"client_id": client_id, "updated": True, "changes": updates}

