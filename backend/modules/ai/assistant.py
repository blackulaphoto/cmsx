"""
AI Assistant Core
Handles OpenAI Assistant API integration and conversation management
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Fix for httpx proxies parameter issue - Apply patch before importing OpenAI
import httpx

# Store original client init
original_client_init = httpx.Client.__init__

def patched_client_init(self, *args, **kwargs):
    """Patched httpx.Client.__init__ that removes problematic parameters"""
    # Remove parameters that cause issues
    problematic_params = ['proxies', 'mounts', 'app']
    
    for param in problematic_params:
        if param in kwargs:
            logger.debug(f"Removing problematic httpx parameter: {param}")
            kwargs.pop(param)
    
    return original_client_init(self, *args, **kwargs)

# Apply the patch
httpx.Client.__init__ = patched_client_init

# Now import OpenAI
import openai
from openai import OpenAI

from .data_access import PlatformDataAccess
from .functions import PLATFORM_FUNCTIONS, FunctionHandler

logger = logging.getLogger(__name__)

class AIAssistant:
    """Main AI Assistant class for Second Chance Jobs platform"""
    
    def __init__(self):
        # Initialize OpenAI client with proper error handling
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            
            if not api_key:
                raise ValueError("OpenAI API key not found")
                
            self.client = OpenAI(
                api_key=api_key,
                default_headers={"OpenAI-Beta": "assistants=v2"}
            )
            logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
            
        self.assistant_id = "asst_eMFylj7t0Yas5wlC9zSkeygA"
        
        # Initialize data access and function handler
        self.data_access = PlatformDataAccess()
        self.function_handler = FunctionHandler(self.data_access)
        
        # Thread management
        self.active_threads = {}
        
        # Assistant configuration
        self.assistant_config = {
            "name": "Second Chance AI Assistant",
            "instructions": self._get_system_instructions(),
            "tools": [{"type": "function", "function": func} for func in PLATFORM_FUNCTIONS],
            "model": "gpt-4-1106-preview"
        }
        
        # Initialize or update assistant
        self._setup_assistant()
    
    def _get_system_instructions(self) -> str:
        """Get system instructions for the AI assistant"""
        return """
You are the AI Assistant for the Second Chance Jobs platform, designed to help people with criminal backgrounds find employment, housing, and support services. You have access to comprehensive platform data and can help both case managers and clients.

## Your Role:
- **Supportive & Non-judgmental**: Always maintain a respectful, encouraging tone
- **Knowledgeable**: You have access to job listings, housing resources, legal services, and client case management data
- **Action-oriented**: Provide specific, actionable advice and next steps
- **Privacy-conscious**: Protect sensitive client information and only share appropriate details

## Key Capabilities:
1. **Job Search**: Find background-friendly employment opportunities
2. **Housing Assistance**: Locate transitional housing, sober living, and background-friendly housing
3. **Case Management**: Access client information, tasks, appointments, and referrals
4. **Legal Support**: Find legal aid resources and track court dates
5. **Service Coordination**: Connect users with mental health, job training, and support services
6. **Resume Help**: Assist with resume building and job application strategies
7. **Web Search**: Search the internet for real-time information and resources
8. **Enhanced Service Search**: Use advanced AI-powered search with quality scoring and comprehensive analysis

## Communication Style:
- Use clear, professional language
- Be empathetic and understanding
- Provide specific examples and actionable steps
- Ask clarifying questions when needed
- Celebrate successes and progress

## Data Access:
You can access real-time platform data including:
- Client profiles and case management information
- Job listings with background-friendly scoring
- Housing resources database
- Service provider directory
- Legal aid resources
- Resume and application tracking
- Web search results with quality scoring
- Enhanced service discovery with AI analysis

## Privacy & Ethics:
- Only access client data when appropriate and authorized
- Maintain confidentiality of sensitive information
- Focus on empowerment and positive outcomes
- Respect user privacy and consent

Remember: Your goal is to help people rebuild their lives and find success despite past challenges. Every interaction should move them closer to stability, employment, and independence.
"""
    
    def _setup_assistant(self):
        """Initialize or update the OpenAI assistant"""
        try:
            # Try to retrieve existing assistant with v2 API
            assistant = self.client.beta.assistants.retrieve(
                assistant_id=self.assistant_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            logger.info(f"Retrieved existing assistant: {assistant.name}")
            
            # Update assistant with current configuration
            self.client.beta.assistants.update(
                assistant_id=self.assistant_id,
                instructions=self.assistant_config["instructions"],
                tools=self.assistant_config["tools"],
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            logger.info("Assistant updated with current configuration")
            
        except Exception as e:
            logger.error(f"Error setting up assistant: {e}")
            # Could create a new assistant here if needed
    
    def process_message(self, message: str, user_id: str, conversation_history: List[Dict] = None, user_context: Dict = None) -> Dict[str, Any]:
        """Process a user message through the AI assistant"""
        try:
            # Get or create thread for user
            thread_id = self._get_or_create_thread(user_id)
            
            # Add user message to thread
            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            # Add context if provided (skip for simple requests to avoid timeouts)
            if conversation_history and len(conversation_history) > 0:
                context_message = self._build_context_message(user_context, conversation_history)
                if context_message:
                    self.client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=context_message,
                        extra_headers={"OpenAI-Beta": "assistants=v2"}
                    )
            
            # Run the assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.assistant_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            # Wait for completion and handle function calls
            response = self._wait_for_completion(thread_id, run.id)
            
            return response
            
        except openai.RateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded: {e}")
            return self._generate_fallback_response(message)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._generate_fallback_response(message)
    
    def _get_or_create_thread(self, user_id: str) -> str:
        """Get existing thread or create new one for user"""
        if user_id in self.active_threads:
            return self.active_threads[user_id]
        
        # Create new thread
        thread = self.client.beta.threads.create(
            extra_headers={"OpenAI-Beta": "assistants=v2"}
        )
        self.active_threads[user_id] = thread.id
        
        logger.info(f"Created new thread {thread.id} for user {user_id}")
        return thread.id
    
    def _build_context_message(self, user_context: Dict = None, conversation_history: List[Dict] = None) -> str:
        """Build context message for the assistant"""
        context_parts = []
        
        if user_context:
            context_parts.append(f"Current page: {user_context.get('page', 'unknown')}")
            if user_context.get('user'):
                context_parts.append(f"User context: {json.dumps(user_context['user'])}")
        
        if conversation_history:
            context_parts.append("Recent conversation context:")
            for entry in conversation_history[-3:]:  # Last 3 exchanges
                context_parts.append(f"User: {entry.get('user', '')}")
                context_parts.append(f"AI: {entry.get('ai', '')}")
        
        return "\n".join(context_parts) if context_parts else ""
    
    def _wait_for_completion(self, thread_id: str, run_id: str, max_iterations: int = 30) -> Dict[str, Any]:
        """Wait for run completion and handle function calls"""
        import time
        
        for iteration in range(max_iterations):
            try:
                # Check run status
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run_id,
                    extra_headers={"OpenAI-Beta": "assistants=v2"}
                )
                
                logger.info(f"Run status (iteration {iteration + 1}): {run.status}")
                
                if run.status == "completed":
                    # Get the assistant's response
                    messages = self.client.beta.threads.messages.list(
                        thread_id=thread_id,
                        order="desc",
                        limit=1,
                        extra_headers={"OpenAI-Beta": "assistants=v2"}
                    )
                    
                    if messages.data:
                        message_content = messages.data[0].content[0].text.value
                        return {
                            "success": True,
                            "message": message_content,
                            "type": "text_response"
                        }
                    else:
                        return {
                            "success": False,
                            "message": "No response received from assistant"
                        }
                
                elif run.status == "requires_action":
                    # Handle function calls
                    tool_calls = run.required_action.submit_tool_outputs.tool_calls
                    tool_outputs = []
                    
                    for tool_call in tool_calls:
                        function_name = tool_call.function.name
                        function_args = json.loads(tool_call.function.arguments)
                        
                        logger.info(f"Executing function: {function_name}")
                        
                        # Execute the function
                        result = self.function_handler.execute_function(function_name, function_args)
                        
                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })
                    
                    # Submit tool outputs
                    self.client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run_id,
                        tool_outputs=tool_outputs,
                        extra_headers={"OpenAI-Beta": "assistants=v2"}
                    )
                    
                    # Continue waiting for completion
                    time.sleep(1)
                    continue
                
                elif run.status in ["failed", "cancelled", "expired"]:
                    return {
                        "success": False,
                        "message": f"Assistant run {run.status}: {run.last_error.message if run.last_error else 'Unknown error'}"
                    }
                
                else:
                    # Still running, wait a bit
                    time.sleep(1)
                    continue
                    
            except Exception as e:
                logger.error(f"Error waiting for completion: {e}")
                return {
                    "success": False,
                    "message": "Error processing your request. Please try again."
                }
        
        # Max iterations reached
        return {
            "success": False,
            "message": "Request timed out. Please try again with a simpler question."
        }
    
    def _generate_fallback_response(self, message: str) -> Dict[str, Any]:
        """Generate a fallback response when OpenAI API is not available"""
        message_lower = message.lower()
        
        # Medical facilities search
        if any(keyword in message_lower for keyword in ['medical', 'hospital', 'clinic', 'doctor', 'health', 'healthcare']):
            if 'los angeles' in message_lower or 'la' in message_lower:
                return {
                    "success": True,
                    "message": """I can help you find medical facilities in Los Angeles! Here are some options:

🏥 **Major Medical Centers:**
- UCLA Medical Center (310-825-9111)
- Cedars-Sinai Medical Center (310-423-3277)
- USC Keck Hospital (323-442-8500)
- Good Samaritan Hospital (213-977-2121)

🏥 **Community Health Centers:**
- LA Care Health Plan Community Resource Centers
- Federally Qualified Health Centers (FQHCs)
- Venice Family Clinic (multiple locations)

🏥 **Specialty Services:**
- Los Angeles County Department of Mental Health
- Harbor-UCLA Medical Center
- Martin Luther King Jr. Community Hospital

For more specific needs or to find facilities near you, I recommend:
1. Calling LA Care at 1-888-839-9909
2. Visiting LACareFHP.org
3. Using the California Hospital Association directory

Would you like me to help you find something more specific, like mental health services or a particular type of specialist?""",
                    "type": "medical_facilities"
                }
            else:
                return {
                    "success": True,
                    "message": """I can help you find medical facilities! To provide the best recommendations, could you let me know:

1. What city or area are you looking in?
2. What type of medical service do you need?
3. Do you have insurance, or do you need low-cost options?

In the meantime, here are some general resources:
- **211**: Dial 2-1-1 for local health services
- **Health.gov**: Find healthcare providers by location
- **HRSA Find a Health Center**: For federally qualified health centers

Let me know your location and I can provide more specific recommendations!""",
                    "type": "medical_facilities"
                }
        
        # Disability benefits
        elif any(keyword in message_lower for keyword in ['disability', 'benefits', 'ssdi', 'ssi', 'social security']):
            return {
                "success": True,
                "message": """I can help guide you through the disability benefits process! Here's what you need to know:

📋 **Key Steps for Disability Benefits:**

1. **Gather Documentation:**
   - Medical records and test results
   - Work history and employment records
   - List of medications and treatments
   - Doctor's statements about your condition

2. **Application Process:**
   - Apply online at SSA.gov
   - Call Social Security at 1-800-772-1213
   - Visit your local Social Security office

3. **Timeline:**
   - Initial application: 3-5 months
   - If denied, appeals can take 12-24 months
   - Most applications require at least one appeal

4. **Local Resources:**
   - Disability Rights California: (800) 776-5746
   - Legal Aid Society: Free legal assistance
   - Independent Living Centers: Support services

5. **Important Tips:**
   - Keep copies of all documents
   - Be detailed about how your condition affects daily activities
   - Don't give up if initially denied - appeals are common

Would you like more specific information about any of these steps, or help finding local disability advocates?""",
                "type": "disability_benefits"
            }
        
        # General help
        else:
            return {
                "success": True,
                "message": """Hello! I'm here to help you with employment, housing, and support services. I can assist with:

🔍 **Job Search & Employment:**
- Finding background-friendly job opportunities
- Resume building and interview preparation
- Job training programs

🏠 **Housing Resources:**
- Transitional housing options
- Sober living facilities
- Background-friendly housing

⚖️ **Legal Services:**
- Expungement and record clearing
- Legal aid resources
- Court date reminders

🏥 **Healthcare & Benefits:**
- Medical facilities and health services
- Disability benefits guidance
- Mental health resources

💼 **Case Management:**
- Appointment scheduling
- Document management
- Progress tracking

What would you like help with today? Please let me know your specific needs and I'll provide detailed guidance!""",
                "type": "general_help"
            }
    
    def process_voice_input(self, audio_file) -> Dict[str, Any]:
        """Process voice input using OpenAI Whisper"""
        try:
            # Transcribe audio to text
            transcript = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
            return {
                "success": True,
                "text": transcript.text
            }
            
        except Exception as e:
            logger.error(f"Error processing voice input: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def generate_voice_output(self, text: str, voice: str = "alloy") -> bytes:
        """Generate voice output using OpenAI TTS"""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text
            )
            
            return response.content
            
        except Exception as e:
            logger.error(f"Error generating voice output: {e}")
            return None
    
    def get_conversation_summary(self, thread_id: str) -> Dict[str, Any]:
        """Get summary of conversation in thread"""
        try:
            messages = self.client.beta.threads.messages.list(
                thread_id=thread_id,
                order="desc",
                limit=20,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            conversation = []
            for message in reversed(messages.data):
                role = message.role
                content = message.content[0].text.value if message.content else ""
                conversation.append({
                    "role": role,
                    "content": content,
                    "timestamp": message.created_at
                })
            
            return {
                "success": True,
                "conversation": conversation,
                "message_count": len(conversation)
            }
            
        except Exception as e:
            logger.error(f"Error getting conversation summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def clear_thread(self, user_id: str) -> bool:
        """Clear conversation thread for user"""
        try:
            if user_id in self.active_threads:
                thread_id = self.active_threads[user_id]
                
                # Delete the thread
                self.client.beta.threads.delete(
                    thread_id,
                    extra_headers={"OpenAI-Beta": "assistants=v2"}
                )
                
                # Remove from active threads
                del self.active_threads[user_id]
                
                logger.info(f"Cleared thread for user {user_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error clearing thread: {e}")
            return False
    
    def get_assistant_info(self) -> Dict[str, Any]:
        """Get information about the assistant"""
        try:
            assistant = self.client.beta.assistants.retrieve(
                self.assistant_id,
                extra_headers={"OpenAI-Beta": "assistants=v2"}
            )
            
            return {
                "id": assistant.id,
                "name": assistant.name,
                "model": assistant.model,
                "instructions": assistant.instructions,
                "tools": len(assistant.tools),
                "created_at": assistant.created_at
            }
            
        except Exception as e:
            logger.error(f"Error getting assistant info: {e}")
            return {"error": str(e)}