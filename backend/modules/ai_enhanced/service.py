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
import sqlite3
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
import openai
from openai import AsyncOpenAI
import os
import aiosqlite

from ...core.config import settings
from ...core.container import singleton, IAIService
from ...shared.database.session import get_async_session

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
        self.db_path = os.path.join("databases", "ai_assistant.db")
    
    async def initialize(self) -> None:
        """Initialize the AI service with OpenAI client and function registry."""
        if self._initialized:
            return
        
        try:
            # Initialize OpenAI client
            self.client = AsyncOpenAI(
                api_key=settings.ai.openai_api_key,
                timeout=30.0,
                max_retries=3
            )
            
            # Initialize database for conversation persistence
            await self._init_database()
            
            # Load conversation memory from database
            await self._load_conversation_memory()
            
            # Register available functions
            self._register_functions()
            
            self._initialized = True
            logger.info("AI service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI service: {e}")
            raise
            
    async def _init_database(self) -> None:
        """Initialize the database for conversation persistence."""
        try:
            # Ensure the databases directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create the conversations table if it doesn't exist
            async with aiosqlite.connect(self.db_path) as db:
                # Create conversations table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        metadata TEXT
                    )
                ''')
                
                # Create function_calls table to track AI function usage
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS function_calls (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT,
                        function_name TEXT NOT NULL,
                        parameters TEXT NOT NULL,
                        result TEXT,
                        success INTEGER NOT NULL,
                        error_message TEXT,
                        timestamp TEXT NOT NULL
                    )
                ''')
                
                await db.commit()
                
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
            
    async def _load_conversation_memory(self) -> None:
        """Load conversation memory from database."""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Get all unique user IDs
                async with db.execute('SELECT DISTINCT user_id FROM conversations') as cursor:
                    user_ids = [row['user_id'] async for row in cursor]
                
                # Load conversations for each user
                for user_id in user_ids:
                    async with db.execute(
                        'SELECT * FROM conversations WHERE user_id = ? ORDER BY timestamp',
                        (user_id,)
                    ) as cursor:
                        conversations = []
                        async for row in cursor:
                            metadata = {}
                            if row['metadata']:
                                try:
                                    metadata = json.loads(row['metadata'])
                                except:
                                    pass
                                    
                            conversations.append({
                                "role": row['role'],
                                "content": row['content'],
                                "timestamp": row['timestamp'],
                                **metadata
                            })
                        
                        if conversations:
                            self.conversation_memory[user_id] = conversations
                
                logger.info(f"Loaded conversations for {len(user_ids)} users from database")
        except Exception as e:
            logger.error(f"Failed to load conversation memory: {e}")
            # Continue with empty memory if loading fails
            logger.warning("Continuing with empty conversation memory")
            
    async def _save_conversation_to_db(self, user_id: str, message: Dict[str, Any]) -> None:
        """
        Save a conversation message to the database.
        
        Args:
            user_id: The user ID associated with the conversation
            message: The message to save (contains role and content)
        """
        try:
            # Extract metadata (anything that's not role or content)
            metadata = {k: v for k, v in message.items() if k not in ['role', 'content']}
            metadata_json = json.dumps(metadata) if metadata else None
            
            # Get current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Insert into database
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''
                    INSERT INTO conversations 
                    (user_id, role, content, timestamp, metadata)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (user_id, message['role'], message['content'], timestamp, metadata_json)
                )
                await db.commit()
                
            logger.debug(f"Saved {message['role']} message for user {user_id} to database")
        except Exception as e:
            logger.error(f"Failed to save conversation to database: {e}")
            # Continue without saving to database - we still have in-memory copy
    
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
        })
        
        logger.info(f"Registered {len(self.function_registry)} AI functions")
    
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
            
            # Generate response
            response = await self.client.chat.completions.create(
                model=settings.ai.openai_model,
                messages=messages,
                temperature=settings.ai.openai_temperature,
                max_tokens=settings.ai.openai_max_tokens,
                functions=self._get_function_definitions(),
                function_call="auto"
            )
            
            # Handle function calls
            if response.choices[0].message.function_call:
                function_result = await self._handle_function_call(
                    response.choices[0].message.function_call,
                    context
                )
                
                # Generate follow-up response with function result
                messages.append({
                    "role": "assistant", 
                    "content": None,
                    "function_call": response.choices[0].message.function_call
                })
                messages.append({
                    "role": "function",
                    "name": response.choices[0].message.function_call.name,
                    "content": json.dumps(function_result)
                })
                
                # Get final response
                final_response = await self.client.chat.completions.create(
                    model=settings.ai.openai_model,
                    messages=messages,
                    temperature=settings.ai.openai_temperature,
                    max_tokens=settings.ai.openai_max_tokens
                )
                
                ai_response = final_response.choices[0].message.content
            else:
                ai_response = response.choices[0].message.content
            
            # Store conversation in memory
            if user_id:
                if user_id not in self.conversation_memory:
                    self.conversation_memory[user_id] = []
                
                # Create message objects
                user_message = {"role": "user", "content": prompt}
                assistant_message = {"role": "assistant", "content": ai_response}
                
                # Add to in-memory conversation
                self.conversation_memory[user_id].extend([
                    user_message,
                    assistant_message
                ])
                
                # Keep only last 50 messages per user
                if len(self.conversation_memory[user_id]) > 50:
                    self.conversation_memory[user_id] = self.conversation_memory[user_id][-50:]
                
                # Persist to database
                await self._save_conversation_to_db(user_id, user_message)
                await self._save_conversation_to_db(user_id, assistant_message)
            
            return ai_response
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again later."
    
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
        
        # Extract user_id from parameters if available
        user_id = parameters.get("user_id", None)
        timestamp = datetime.now(timezone.utc).isoformat()
        success = 1
        error_message = None
        result_data = None
        
        try:
            # Execute the function
            function = self.function_registry[function_name]
            result = await function(**parameters)
            result_data = result
            
            # Log successful function call to database
            await self._log_function_call(
                user_id=user_id,
                function_name=function_name,
                parameters=parameters,
                result=result,
                success=True,
                error_message=None
            )
            
            return result
            
        except Exception as e:
            # Log error
            logger.error(f"Error executing function '{function_name}': {e}")
            error_message = str(e)
            success = 0
            
            # Log failed function call to database
            await self._log_function_call(
                user_id=user_id,
                function_name=function_name,
                parameters=parameters,
                result=None,
                success=False,
                error_message=error_message
            )
            
            raise
            
    async def _log_function_call(self, user_id: str, function_name: str, 
                               parameters: Dict[str, Any], result: Any,
                               success: bool, error_message: str = None) -> None:
        """
        Log function call to database for tracking and analytics.
        
        Args:
            user_id: User ID (if available)
            function_name: Name of the function called
            parameters: Parameters passed to the function
            result: Result of the function call
            success: Whether the function call was successful
            error_message: Error message if the function call failed
        """
        try:
            # Convert parameters and result to JSON
            parameters_json = json.dumps(parameters)
            result_json = json.dumps(result) if result is not None else None
            
            # Get current timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            
            # Insert into database
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    '''
                    INSERT INTO function_calls 
                    (user_id, function_name, parameters, result, success, error_message, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (user_id, function_name, parameters_json, result_json, 
                     1 if success else 0, error_message, timestamp)
                )
                await db.commit()
                
            logger.debug(f"Logged function call: {function_name} (success: {success})")
        except Exception as e:
            logger.error(f"Failed to log function call to database: {e}")
            # Continue without logging to database
    
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
    
    def _build_system_message(self, context: Dict[str, Any] = None) -> str:
        """Build a comprehensive system message for the AI."""
        
        base_message = """
        You are an intelligent assistant for the Second Chance Jobs Platform, a comprehensive case management system 
        designed to help individuals with criminal backgrounds successfully reintegrate into society.
        
        Your role is to:
        1. Provide helpful, empathetic, and practical assistance
        2. Help case managers and clients navigate available services
        3. Generate intelligent task recommendations and reminders
        4. Analyze client situations and suggest appropriate interventions
        5. Maintain a professional, supportive, and non-judgmental tone
        
        You have access to various platform functions to:
        - Create and manage tasks
        - Access client information
        - Schedule appointments
        - Search for resources
        - Generate case notes
        - Analyze risk factors
        
        Always prioritize client safety, privacy, and successful outcomes.
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
        """
        Search for resources using Google Custom Search Engine.
        
        Args:
            query: The search query
            resource_type: Type of resource to search for (housing, jobs, benefits, legal, general)
            location: Location for the search
            
        Returns:
            List of search results
        """
        try:
            # Import the search coordinator
            from ...search.coordinator import SimpleSearchCoordinator, SearchType
            
            # Initialize search coordinator
            coordinator = SimpleSearchCoordinator()
            
            # Map resource type to search type
            search_type_map = {
                "housing": SearchType.HOUSING,
                "jobs": SearchType.JOBS,
                "services": SearchType.SERVICES,
                "benefits": SearchType.SERVICES,
                "legal": SearchType.SERVICES,
                "general": SearchType.GENERAL
            }
            
            # Get the appropriate search type
            search_type = search_type_map.get(resource_type.lower(), SearchType.GENERAL)
            
            # Set default location if not provided
            if not location:
                location = "Los Angeles, CA"
                
            logger.info(f"Searching for {resource_type} resources with query: '{query}' in {location}")
            
            # Perform the search
            search_results = coordinator.search(query, search_type, location)
            
            # Format the results
            formatted_results = []
            for item in search_results.get("results", []):
                formatted_results.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                    "source": item.get("source", ""),
                    "type": resource_type,
                    "location": location,
                    "confidence_score": item.get("confidence_score", 0.0)
                })
                
            logger.info(f"Found {len(formatted_results)} {resource_type} resources for query: '{query}'")
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Error searching for resources: {e}")
            # Return a minimal fallback result if search fails
            return [
                {
                    "title": f"Resource for {query}",
                    "type": resource_type,
                    "location": location,
                    "description": f"Helpful resource related to {query}",
                    "url": "",
                    "source": "fallback",
                    "error": str(e)
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
    
    async def _update_client_status(self, client_id: str, **updates) -> Dict[str, Any]:
        """Update client status."""
        # Mock implementation
        return {"client_id": client_id, "updated": True, "changes": updates}

