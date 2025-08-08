#!/usr/bin/env python3
"""
Simple AI Assistant for Second Chance Jobs Platform
Enhanced with real platform data access for case management
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import requests

logger = logging.getLogger(__name__)

class SimpleAIAssistant:
    """Simple AI Assistant using OpenAI Chat Completions API with real platform data"""
    
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = "https://api.openai.com/v1"
        self.model = "gpt-4o"
        self.platform_base_url = "http://127.0.0.1:8002"
        
        # Initialize conversation history
        self.conversations = {}
        
        # Enhanced system message with platform integration
        self.system_message = """
You are the AI Assistant for the Second Chance Jobs platform, designed to help people with criminal backgrounds find employment, housing, and support services.

## Your Enhanced Capabilities:

### Real Platform Data Access:
- **Client Management**: Access to actual client records and case information
- **Housing Resources**: Real-time housing search with background-friendly options  
- **Services Coordination**: Connect users with actual service providers in the system
- **Case Updates**: Help case managers track appointments, referrals, and progress

### REAL EXTERNAL SEARCH CAPABILITY:
- **Multi-State Resources**: When asked for resources in specific cities/states, you have access to REAL search results from live APIs
- **Verified Information**: Use actual search results from SERPER and Google APIs for current, real information
- **Live Contact Data**: Provide real phone numbers, addresses, and websites from search results
- **Never Fabricate**: ALWAYS use real search results when provided, never make up fake information

### Your Role:
- **Supportive & Non-judgmental**: Always maintain a respectful, encouraging tone
- **Data-Driven**: Use actual platform data and real search results to provide specific, accurate information
- **Action-oriented**: Provide concrete next steps using real resources
- **Privacy-conscious**: Protect sensitive information while being helpful
- **Accurate**: Only provide verified information from real sources

### Key Functions:
1. **Case Management**: "What clients do we have?" - Access client database
2. **Housing Search**: "Find housing for [client]" - Search actual housing resources AND external real resources
3. **Service Referrals**: "What services are available?" - Access service provider database
4. **Job Matching**: Help match clients with background-friendly employment
5. **Real Resource Search**: When asked for resources in specific locations, use REAL search results provided

### IMPORTANT: When external search results are provided in your context, you MUST:
1. Use ONLY the real search results provided
2. Include actual phone numbers, addresses, and websites
3. Never fabricate or make up information
4. Clearly indicate when information comes from live search results
5. Format the real results professionally with all contact details

### CRITICAL: Empty Data Handling:
- If no tasks are found (task_count = 0), respond with "You currently have no tasks scheduled. Would you like me to help you create some tasks or check your client caseload?"
- If no clients are found, offer to help with client intake
- If no data is available, acknowledge this honestly and offer assistance
- NEVER fabricate fake clients, tasks, or appointments when data is empty
- Always be truthful about what information is actually available in the system

### Platform Integration Commands:
- When asked about clients: Use /api/ai/data/clients
- When asked about housing: Use /api/ai/data/housing  
- When asked about services: Use /api/ai/data/services
- Always provide specific, actionable information from real data

### Communication Style:
- Use actual data when available
- Provide specific names, phone numbers, and addresses
- Give concrete next steps
- Be professional yet empathetic
- Focus on solutions and opportunities

Remember: You have access to real platform data. Use it to provide specific, helpful information that moves people toward stability and success.
"""
    
    def get_platform_data(self, endpoint: str) -> Dict[str, Any]:
        """Get data from platform endpoints"""
        try:
            response = requests.get(f"{self.platform_base_url}{endpoint}", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Platform API error: {response.status_code} for {endpoint}")
                return {'success': False, 'error': 'API unavailable'}
        except Exception as e:
            logger.warning(f"Platform data access failed for {endpoint}: {e}")
            return {'success': False, 'error': str(e)}
    
    def process_message(self, message: str, user_id: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """Process a user message with enhanced platform data access"""
        try:
            # Check if message requires platform data
            platform_context = self._get_relevant_platform_data(message)
            
            # Build conversation messages with context
            messages = [{"role": "system", "content": self.system_message}]
            
            # Add platform context if available
            if platform_context:
                context_message = f"Platform Data Context: {json.dumps(platform_context, indent=2)}"
                messages.append({"role": "system", "content": context_message})
            
            # Add conversation history if provided
            if conversation_history:
                for entry in conversation_history[-5:]:  # Last 5 exchanges
                    if entry.get('user'):
                        messages.append({"role": "user", "content": entry['user']})
                    if entry.get('ai'):
                        messages.append({"role": "assistant", "content": entry['ai']})
            
            # Add current message
            messages.append({"role": "user", "content": message})
            
            # Make API request
            response = self._make_openai_request(messages)
            
            if response.get('success'):
                return {
                    "success": True,
                    "message": response.get('message', ''),
                    "type": "ai_response",
                    "platform_data_used": bool(platform_context)
                }
            else:
                # Fall back to enhanced responses with any available data
                return self._generate_enhanced_fallback_response(message, platform_context)
                
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return self._generate_enhanced_fallback_response(message)
    
    def _get_relevant_platform_data(self, message: str) -> Dict[str, Any]:
        """Get relevant platform data based on message content"""
        message_lower = message.lower()
        context = {}
        
        # Client-related queries
        if any(keyword in message_lower for keyword in ['client', 'case', 'who do we have', 'clients']):
            clients_data = self.get_platform_data('/api/ai/data/clients')
            if clients_data.get('success'):
                context['clients'] = clients_data.get('clients', [])
        
        # Task-related queries - FIXED to handle empty tasks gracefully
        if any(keyword in message_lower for keyword in ['task', 'tasks', 'todo', 'schedule', 'today', 'reminder']):
            try:
                # Try to get actual tasks from the smart dashboard
                dashboard_data = self.get_platform_data('/api/reminders/smart-dashboard/test_manager')
                if dashboard_data.get('success'):
                    dashboard = dashboard_data.get('dashboard', {})
                    today_tasks = dashboard.get('today_tasks', [])
                    context['tasks_today'] = today_tasks
                    context['task_count'] = len(today_tasks)
                    context['has_tasks'] = len(today_tasks) > 0
                else:
                    # Explicitly set empty task context
                    context['tasks_today'] = []
                    context['task_count'] = 0
                    context['has_tasks'] = False
                    context['task_system_status'] = 'No tasks found in system'
            except Exception as e:
                logger.warning(f"Task data access failed: {e}")
                context['tasks_today'] = []
                context['task_count'] = 0
                context['has_tasks'] = False
                context['task_system_status'] = 'Task system unavailable'
        
        # Housing-related queries with real search capability
        if any(keyword in message_lower for keyword in ['housing', 'home', 'apartment', 'place to live', 'shelter', 'sober living']):
            # First, get platform housing resources
            housing_data = self.get_platform_data('/api/ai/data/housing')
            if housing_data.get('success'):
                context['housing_resources'] = housing_data.get('housing_resources', [])
            
            # Check if user is asking for resources in specific locations
            locations = []
            location_patterns = [
                (r'houston[,\s]+tx|houston[,\s]+texas', 'Houston, TX'),
                (r'miami[,\s]+fl|miami[,\s]+florida', 'Miami, FL'),
                (r'chicago[,\s]+il|chicago[,\s]+illinois', 'Chicago, IL'),
                (r'los angeles[,\s]+ca|la[,\s]+california', 'Los Angeles, CA'),
                (r'new york[,\s]+ny|nyc', 'New York, NY'),
                (r'atlanta[,\s]+ga|atlanta[,\s]+georgia', 'Atlanta, GA')
            ]
            
            import re
            for pattern, location in location_patterns:
                if re.search(pattern, message_lower):
                    locations.append(location)
            
            # If specific locations mentioned, search for real resources
            if locations:
                context['external_search_needed'] = True
                context['search_locations'] = locations
                
                # Perform real search for each location
                real_resources = []
                for location in locations:
                    search_query = "sober living transitional housing recovery homes background friendly"
                    location_resources = self._search_real_resources(search_query, location)
                    real_resources.extend(location_resources)
                
                context['real_housing_resources'] = real_resources
                logger.info(f"Found {len(real_resources)} real resources for locations: {locations}")
        
        # Mental health and counseling services
        if any(keyword in message_lower for keyword in ['mental health', 'therapy', 'counseling', 'therapist', 'counselor', 'psychiatric', 'psychology']):
            # Get platform service provider data
            services_data = self.get_platform_data('/api/ai/data/services')
            if services_data.get('success'):
                context['service_providers'] = services_data.get('service_providers', [])
            
            # Check if user is asking for services in specific locations
            locations = []
            location_patterns = [
                (r'houston[,\s]+tx|houston[,\s]+texas', 'Houston, TX'),
                (r'miami[,\s]+fl|miami[,\s]+florida', 'Miami, FL'),
                (r'chicago[,\s]+il|chicago[,\s]+illinois', 'Chicago, IL'),
                (r'los angeles[,\s]+ca|la[,\s]+california', 'Los Angeles, CA'),
                (r'new york[,\s]+ny|nyc', 'New York, NY'),
                (r'atlanta[,\s]+ga|atlanta[,\s]+georgia', 'Atlanta, GA')
            ]
            
            import re
            for pattern, location in location_patterns:
                if re.search(pattern, message_lower):
                    locations.append(location)
            
            # If specific locations mentioned, search for real mental health resources
            if locations:
                context['external_search_needed'] = True
                context['search_locations'] = locations
                
                # Perform real search for mental health services
                real_services = []
                for location in locations:
                    search_query = "mental health counseling therapy criminal background friendly affordable"
                    location_services = self._search_real_resources(search_query, location)
                    real_services.extend(location_services)
                
                context['real_mental_health_services'] = real_services
                logger.info(f"Found {len(real_services)} real mental health services for locations: {locations}")
        
        # Legal services and document preparation
        if any(keyword in message_lower for keyword in ['legal', 'court', 'probation', 'hearing', 'expungement', 'document', 'checklist', 'lawyer', 'attorney']):
            # Get platform legal documents data
            documents_data = self.get_platform_data('/api/documents/list')
            if documents_data.get('success'):
                context['legal_documents'] = documents_data.get('documents', [])
            
            # Get legal cases data
            cases_data = self.get_platform_data('/api/legal/cases')
            if cases_data.get('success'):
                context['legal_cases'] = cases_data.get('cases', [])
        
        return context
    
    def _make_openai_request(self, messages: List[Dict]) -> Dict[str, Any]:
        """Make request to OpenAI API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                message = result['choices'][0]['message']['content']
                return {
                    "success": True,
                    "message": message
                }
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}"
                }
                
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _generate_enhanced_fallback_response(self, message: str, platform_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate enhanced fallback response with platform data when available"""
        message_lower = message.lower()
        
        # Client management queries with real data
        if any(keyword in message_lower for keyword in ['client', 'case', 'who do we have', 'clients']):
            clients = platform_context.get('clients', []) if platform_context else []
            if clients:
                client_info = []
                for client in clients:
                    client_info.append(f"• **{client['name']}** (ID: {client['client_id'][:8]}...)")
                    client_info.append(f"  Status: {client['case_status']} | Phone: {client['phone']}")
                    if client['next_appointment']:
                        client_info.append(f"  Next Appointment: {client['next_appointment']}")
                
                return {
                    "success": True,
                    "message": f"""📋 **Current Active Clients ({len(clients)})**

{chr(10).join(client_info)}

**Available Actions:**
- Schedule appointments
- Add case notes
- Update case status
- Create service referrals

Would you like me to help with any specific client or case management task?""",
                    "type": "case_management_data"
                }
            else:
                return {
                    "success": True,
                    "message": "📋 **Client Management**\n\nI can help you manage client cases, but I don't see any active clients in the system right now. Would you like to:\n\n1. Add a new client to the system\n2. Search for existing clients\n3. View inactive clients\n4. Get help with case management features",
                    "type": "case_management_help"
                }
        
        # Housing search with real data
        if any(keyword in message_lower for keyword in ['housing', 'home', 'apartment', 'place to live', 'shelter']):
            housing = platform_context.get('housing_resources', []) if platform_context else []
            if housing:
                housing_info = []
                for resource in housing:
                    cost_text = f"${resource['cost']}/month" if resource['cost'] > 0 else "Free"
                    housing_info.append(f"• **{resource['name']}** ({resource['type']})")
                    housing_info.append(f"  📍 {resource['location']} | 📞 {resource['phone']}")
                    housing_info.append(f"  💰 {cost_text} | ✅ Background-friendly")
                    if resource['services']:
                        housing_info.append(f"  🔧 Services: {resource['services']}")
                    housing_info.append("")
                
                return {
                    "success": True,
                    "message": f"""🏠 **Available Housing Resources ({len(housing)})**

{chr(10).join(housing_info)}

**Next Steps:**
1. Call the facility directly to inquire about availability
2. Ask about their specific background policies
3. Schedule a tour or intake appointment
4. Gather required documents for application

Which housing resource would you like more information about?""",
                    "type": "housing_data"
                }
        
        # Mental health services with real data
        if any(keyword in message_lower for keyword in ['mental health', 'therapy', 'counseling', 'therapist', 'counselor', 'psychiatric']):
            services = platform_context.get('service_providers', []) if platform_context else []
            if services:
                service_info = []
                for service in services:
                    service_info.append(f"• **{service['name']}** ({service['type']})")
                    service_info.append(f"  📍 {service['location']} | 📞 {service['phone']}")
                    service_info.append(f"  🏢 {service['address']}")
                    service_info.append(f"  ✅ Background-friendly | 💰 {service['cost_info']}")
                    if service['services']:
                        service_info.append(f"  🔧 Services: {service['services']}")
                    service_info.append("")
                
                return {
                    "success": True,
                    "message": f"""🧠 **Available Mental Health Services ({len(services)})**

{chr(10).join(service_info)}

**Next Steps:**
1. Call the provider directly to schedule an intake appointment
2. Ask about their experience with clients with criminal backgrounds
3. Inquire about payment options and insurance acceptance
4. Discuss your specific mental health needs and goals

Which mental health provider would you like more information about?""",
                    "type": "mental_health_data"
                }
        
        # Legal services and document preparation with real data
        if any(keyword in message_lower for keyword in ['legal', 'court', 'probation', 'hearing', 'expungement', 'document', 'checklist']):
            documents = platform_context.get('legal_documents', []) if platform_context else []
            cases = platform_context.get('legal_cases', []) if platform_context else []
            
            if documents or cases:
                response_parts = []
                
                if 'probation' in message_lower and 'hearing' in message_lower:
                    response_parts.append("⚖️ **Probation Review Hearing Document Checklist**\n")
                    response_parts.append("**Required Documents:**")
                    response_parts.append("1. **Proof of Employment** - Pay stubs, employment letter, or job search documentation")
                    response_parts.append("2. **Program Completion Certificates** - Drug treatment, anger management, community service")
                    response_parts.append("3. **Character Reference Letters** - From employers, counselors, community members")
                    response_parts.append("4. **Updated Contact Information** - Current address, phone number, emergency contacts")
                    response_parts.append("5. **Payment Records** - Receipts for fines, fees, restitution payments")
                    response_parts.append("6. **Community Service Verification** - Hours completed, supervisor contact info")
                    response_parts.append("")
                    response_parts.append("**Evidence of Rehabilitation:**")
                    response_parts.append("• Steady employment or education enrollment")
                    response_parts.append("• Completion of court-ordered programs")
                    response_parts.append("• Positive drug/alcohol tests")
                    response_parts.append("• Community involvement and volunteer work")
                    response_parts.append("• Stable housing situation")
                    response_parts.append("• Strong support system documentation")
                
                elif 'expungement' in message_lower:
                    response_parts.append("📋 **Expungement Application Document Checklist**\n")
                    response_parts.append("**Required Documents:**")
                    response_parts.append("1. **Certified Copy of Conviction Record** - From court clerk")
                    response_parts.append("2. **Proof of Sentence Completion** - Probation completion letter")
                    response_parts.append("3. **Character Reference Letters** - 3-5 letters from employers, community leaders")
                    response_parts.append("4. **Employment History** - Resume, employment verification letters")
                    response_parts.append("5. **Community Involvement** - Volunteer work, civic participation")
                    response_parts.append("6. **Rehabilitation Program Certificates** - Treatment programs, education")
                
                if documents:
                    response_parts.append(f"\n**Available Legal Documents ({len(documents)}):**")
                    for doc in documents[:3]:  # Show first 3 documents
                        response_parts.append(f"• **{doc['title']}** - {doc['document_type']}")
                        if doc.get('description'):
                            response_parts.append(f"  {doc['description']}")
                
                response_parts.append("\n**Next Steps:**")
                response_parts.append("1. Gather all required documents listed above")
                response_parts.append("2. Make copies of all original documents")
                response_parts.append("3. Contact your probation officer or attorney for guidance")
                response_parts.append("4. Schedule your hearing or file your petition")
                
                return {
                    "success": True,
                    "message": chr(10).join(response_parts),
                    "type": "legal_guidance"
                }
        
        
        # Default enhanced responses based on context
        if platform_context:
            return {
                "success": True,
                "message": f"""🤖 **Second Chance Platform Assistant**

I have access to your platform data and can help with:

**Available Information:**
{f"• {len(platform_context.get('clients', []))} active clients" if 'clients' in platform_context else ""}
{f"• {len(platform_context.get('housing_resources', []))} housing resources" if 'housing_resources' in platform_context else ""}

**How can I help you today?**
- Case management and client tracking
- Housing search and referrals
- Service coordination
- Progress updates and reporting

Please let me know what specific information or task you need assistance with!""",
                "type": "enhanced_help"
            }
        
        # Standard fallback
        return self._generate_fallback_response(message)
    
    def _generate_fallback_response(self, message: str) -> Dict[str, Any]:
        """Generate standard fallback response when OpenAI API is not available"""
        message_lower = message.lower()
        
        # Job search help
        if any(keyword in message_lower for keyword in ['job', 'work', 'employment', 'hire', 'career']):
            return {
                "success": True,
                "message": """🔍 **Job Search Help**

I can help you find background-friendly employment opportunities! Here are some strategies:

**Background-Friendly Industries:**
- Construction and skilled trades
- Warehousing and logistics
- Food service and hospitality
- Retail and customer service
- Transportation and delivery
- Manufacturing and production

**Job Search Tips:**
1. **Focus on smaller companies** - They often have more flexible hiring practices
2. **Look for "second chance" employers** - Many companies actively hire people with backgrounds
3. **Consider temp agencies** - They can be a good way to get your foot in the door
4. **Network through support groups** - Other people in recovery often know understanding employers
5. **Be upfront when appropriate** - Honesty can sometimes work in your favor

Would you like me to help you with a specific type of job search, or do you have questions about resume building or interview preparation?""",
                "type": "job_search_help"
            }
        
        # General help
        return {
            "success": True,
            "message": """👋 **Welcome to Second Chance Jobs Platform!**

I'm here to help you rebuild your life and find success despite past challenges. I can assist with:

🔍 **Employment Support:**
- Finding background-friendly job opportunities
- Resume building and job application tips
- Interview preparation and strategies
- Career planning and skill development

🏠 **Housing Assistance:**
- Transitional housing programs
- Background-friendly rental options
- Emergency shelter information
- Housing application guidance

⚖️ **Legal Resources:**
- Expungement and record sealing
- Legal aid organizations
- Court preparation assistance
- Know your rights information

🏥 **Healthcare & Services:**
- Medical care resources
- Mental health support
- Substance abuse treatment
- Benefits and social services

💼 **Case Management:**
- Goal setting and progress tracking
- Connecting with local resources
- Appointment scheduling
- Document assistance

What would you like help with today? I'm here to support you every step of the way! 🌟""",
            "type": "general_help"
        }
    
    def process_voice_input(self, audio_data: bytes) -> Dict[str, Any]:
        """Process voice input - placeholder for future implementation"""
        return {
            "success": False,
            "message": "Voice input processing is not yet implemented. Please type your message."
        }
    
    def generate_voice_output(self, text: str) -> bytes:
        """Generate voice output - placeholder for future implementation"""
        return None
    
    def get_response(self, message: str, conversation_id: str = None, client_id: str = None, context: Dict[str, Any] = None) -> str:
        """Get response from AI assistant - compatibility method for routes"""
        try:
            # Use the existing process_message method
            user_id = client_id or conversation_id or "default_user"
            
            # Get conversation history if available
            conversation_history = []
            if conversation_id and conversation_id in self.conversations:
                conversation_history = self.conversations[conversation_id]
            
            # Process the message
            result = self.process_message(message, user_id, conversation_history)
            
            # Store conversation if successful
            if result.get('success') and conversation_id:
                if conversation_id not in self.conversations:
                    self.conversations[conversation_id] = []
                
                self.conversations[conversation_id].append({
                    'user': message,
                    'ai': result.get('message', ''),
                    'timestamp': datetime.now().isoformat(),
                    'context': context or {}
                })
            
            # Return the message content
            return result.get('message', 'I apologize, but I encountered an error processing your request.')
            
        except Exception as e:
            logger.error(f"Error in get_response: {e}")
            return f"I apologize, but I encountered an error: {str(e)}"

    def _search_real_resources(self, query: str, location: str = None) -> List[Dict[str, Any]]:
        """Search for real resources using external APIs"""
        try:
            # Construct search query for sober living/housing resources
            search_query = f"{query}"
            if location:
                search_query += f" in {location}"
            
            # Add specific keywords for better results with contact info
            search_query += " sober living transitional housing recovery homes contact phone address directory"
            
            # First try SERPER API (more reliable for real-time search)
            serper_results = self._serper_search(search_query)
            if serper_results:
                processed_serper = self._process_search_results(serper_results, location)
                if processed_serper:
                    return processed_serper
            
            # Fallback to Google Custom Search
            google_results = self._google_search(search_query)
            if google_results:
                processed_google = self._process_search_results(google_results, location)
                
                # Also try a more specific contact search
                if location:
                    contact_query = f"sober living recovery homes {location} phone contact directory"
                    contact_results = self._google_search(contact_query)
                    if contact_results:
                        processed_contact = self._process_search_results(contact_results, location)
                        # Merge unique results
                        all_results = processed_google + processed_contact
                        unique_results = []
                        seen_names = set()
                        for result in all_results:
                            name = result.get('name', '').lower()
                            if name not in seen_names:
                                seen_names.add(name)
                                unique_results.append(result)
                        return unique_results[:5]  # Limit to 5 best results
                
                return processed_google
                
            return []
            
        except Exception as e:
            logger.error(f"Error searching real resources: {e}")
            return []
    
    def _serper_search(self, query: str) -> List[Dict[str, Any]]:
        """Search using SERPER API for real results"""
        try:
            serper_key = os.getenv('SERPER_API_KEY')
            if not serper_key:
                return []
                
            url = "https://google.serper.dev/search"
            payload = {
                "q": query,
                "num": 10,
                "type": "search"
            }
            headers = {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('organic', [])
            
            return []
            
        except Exception as e:
            logger.error(f"SERPER search error: {e}")
            return []
    
    def _google_search(self, query: str) -> List[Dict[str, Any]]:
        """Search using Google Custom Search API"""
        try:
            google_key = os.getenv('GOOGLE_API_KEY')
            cse_id = os.getenv('GOOGLE_CSE_ID')
            
            if not google_key or not cse_id:
                return []
                
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": google_key,
                "cx": cse_id,
                "q": query,
                "num": 10
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('items', [])
                
            return []
            
        except Exception as e:
            logger.error(f"Google search error: {e}")
            return []
    
    def _process_search_results(self, results: List[Dict[str, Any]], location: str) -> List[Dict[str, Any]]:
        """Process search results to extract contact information"""
        processed = []
        
        for result in results[:5]:  # Limit to top 5 results
            try:
                title = result.get('title', '')
                snippet = result.get('snippet', result.get('description', ''))
                link = result.get('link', result.get('url', ''))
                
                # Extract phone numbers using regex
                import re
                phone_pattern = r'(\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})'
                phones = re.findall(phone_pattern, snippet + ' ' + title)
                
                # Look for address information (more flexible)
                address_keywords = ['address', 'located', 'street', 'avenue', 'drive', 'road', 'blvd', 'lane']
                address = None
                for keyword in address_keywords:
                    if keyword in snippet.lower():
                        # Extract potential address
                        parts = snippet.split('.')
                        for part in parts:
                            if keyword in part.lower():
                                address = part.strip()
                                break
                        if address:
                            break
                
                # More inclusive criteria - include if it's recovery/housing related
                is_relevant = (
                    'sober living' in (title + snippet).lower() or 
                    'recovery' in (title + snippet).lower() or
                    'transitional housing' in (title + snippet).lower() or
                    'treatment center' in (title + snippet).lower() or
                    'oxford house' in (title + snippet).lower() or
                    'halfway house' in (title + snippet).lower() or
                    'residential treatment' in (title + snippet).lower()
                )
                
                if is_relevant:
                    # Extract phone from website if not in snippet
                    if not phones and 'phone' in snippet.lower():
                        # Look for numbers after "phone", "call", "contact"
                        phone_context = re.search(r'(phone|call|contact).*?(\d{3}[-.]?\d{3}[-.]?\d{4})', snippet, re.IGNORECASE)
                        if phone_context:
                            phones = [phone_context.group(2)]
                    
                    processed.append({
                        'name': title,
                        'description': snippet,
                        'phone': phones[0] if phones else 'Visit website for contact information',
                        'address': address or f'Located in {location} - visit website for specific address',
                        'website': link,
                        'source': 'real_search'
                    })
                    
            except Exception as e:
                logger.error(f"Error processing result: {e}")
                continue
        
        return processed

# Create global instance
ai_assistant = SimpleAIAssistant()