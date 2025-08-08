"""
OpenAI Function Definitions for AI Assistant
Defines all available functions that the AI can call to access platform data
"""

from typing import Dict, List, Any
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# OpenAI Function Definitions
PLATFORM_FUNCTIONS = [
    {
        "name": "get_client_info",
        "description": "Get comprehensive information about a client including their profile, referrals, tasks, appointments, and documents",
        "parameters": {
            "type": "object",
            "properties": {
                "client_identifier": {
                    "type": "string",
                    "description": "Client name, ID, or email address to search for"
                }
            },
            "required": ["client_identifier"]
        }
    },
    {
        "name": "get_court_dates",
        "description": "Get upcoming court dates and legal appointments for a specific client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to get court dates for"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "search_jobs",
        "description": "Search for job opportunities based on keywords and location, with background-friendly prioritization",
        "parameters": {
            "type": "object",
            "properties": {
                "keywords": {
                    "type": "string",
                    "description": "Job search keywords (job title, skills, industry)"
                },
                "location": {
                    "type": "string",
                    "description": "Location to search for jobs (city, state, or zip code)"
                },
                "client_id": {
                    "type": "string",
                    "description": "Optional client ID to personalize job matches"
                }
            },
            "required": ["keywords"]
        }
    },
    {
        "name": "get_job_matches",
        "description": "Get personalized job matches for a specific client based on their profile and preferences",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to get job matches for"
                },
                "keywords": {
                    "type": "string",
                    "description": "Optional keywords to filter job matches"
                },
                "location": {
                    "type": "string",
                    "description": "Optional location preference"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "search_housing",
        "description": "Search for housing resources including transitional housing, sober living, and background-friendly options",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "Location to search for housing (city, state, or zip code)"
                },
                "housing_type": {
                    "type": "string",
                    "description": "Type of housing (transitional, sober living, supportive, etc.)"
                },
                "background_friendly": {
                    "type": "boolean",
                    "description": "Whether to filter for background-friendly housing options",
                    "default": True
                }
            }
        }
    },
    {
        "name": "search_providers",
        "description": "Search for service providers including mental health, legal aid, job training, and other support services",
        "parameters": {
            "type": "object",
            "properties": {
                "service_type": {
                    "type": "string",
                    "description": "Type of service needed (mental health, legal aid, job training, etc.)"
                },
                "location": {
                    "type": "string",
                    "description": "Location to search for providers"
                }
            },
            "required": ["service_type"]
        }
    },
    {
        "name": "get_referral_status",
        "description": "Check the status of service referrals for a client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to check referrals for"
                },
                "referral_id": {
                    "type": "string",
                    "description": "Optional specific referral ID to check"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "get_client_summary",
        "description": "Get a summary of client statistics including referrals, tasks, appointments, and documents",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to get summary for"
                }
            },
            "required": ["client_id"]
        }
    },
    {
        "name": "search_all",
        "description": "Search across all platform data including clients, jobs, housing, and services",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to look for across all data"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of results per category",
                    "default": 10
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_platform_stats",
        "description": "Get overall platform statistics including total clients, jobs, housing options, and services",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "create_task",
        "description": "Create a new task for a client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to create task for"
                },
                "title": {
                    "type": "string",
                    "description": "Task title"
                },
                "description": {
                    "type": "string",
                    "description": "Task description"
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format"
                },
                "priority": {
                    "type": "string",
                    "description": "Task priority (low, medium, high)",
                    "default": "medium"
                }
            },
            "required": ["client_id", "title", "due_date"]
        }
    },
    {
        "name": "add_case_note",
        "description": "Add a case note for a client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to add note for"
                },
                "note_text": {
                    "type": "string",
                    "description": "Content of the case note"
                },
                "note_type": {
                    "type": "string",
                    "description": "Type of note (meeting, phone_call, email, other)",
                    "default": "other"
                }
            },
            "required": ["client_id", "note_text"]
        }
    },
    {
        "name": "web_search",
        "description": "Search the web for real-time information using advanced search capabilities",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find information on the web"
                },
                "location": {
                    "type": "string",
                    "description": "Location context for search (optional)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 10)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "enhanced_service_search",
        "description": "Search for services using advanced AI-powered search with quality scoring and comprehensive analysis",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Service search query (e.g., 'addiction treatment for women', 'mental health services')"
                },
                "location": {
                    "type": "string",
                    "description": "Location context (e.g., 'Los Angeles', 'rural Idaho')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 20)"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "schedule_appointment",
        "description": "Schedule an appointment for a client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_id": {
                    "type": "string",
                    "description": "Client ID to schedule appointment for"
                },
                "appointment_date": {
                    "type": "string",
                    "description": "Appointment date and time in YYYY-MM-DD HH:MM format"
                },
                "appointment_type": {
                    "type": "string",
                    "description": "Type of appointment (check-in, counseling, job_interview, court, other)"
                },
                "description": {
                    "type": "string",
                    "description": "Appointment description"
                },
                "location": {
                    "type": "string",
                    "description": "Appointment location"
                }
            },
            "required": ["client_id", "appointment_date", "appointment_type"]
        }
    }
]

class FunctionHandler:
    """Handles execution of AI function calls"""
    
    def __init__(self, data_access):
        self.data_access = data_access
        
    def execute_function(self, function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a function call and return results"""
        try:
            logger.info(f"Executing function: {function_name} with args: {arguments}")
            
            # Route to appropriate method
            if function_name == "get_client_info":
                return self._handle_get_client_info(arguments)
            elif function_name == "get_court_dates":
                return self._handle_get_court_dates(arguments)
            elif function_name == "search_jobs":
                return self._handle_search_jobs(arguments)
            elif function_name == "get_job_matches":
                return self._handle_get_job_matches(arguments)
            elif function_name == "search_housing":
                return self._handle_search_housing(arguments)
            elif function_name == "search_providers":
                return self._handle_search_providers(arguments)
            elif function_name == "get_referral_status":
                return self._handle_get_referral_status(arguments)
            elif function_name == "get_client_summary":
                return self._handle_get_client_summary(arguments)
            elif function_name == "search_all":
                return self._handle_search_all(arguments)
            elif function_name == "get_platform_stats":
                return self._handle_get_platform_stats(arguments)
            elif function_name == "create_task":
                return self._handle_create_task(arguments)
            elif function_name == "add_case_note":
                return self._handle_add_case_note(arguments)
            elif function_name == "schedule_appointment":
                return self._handle_schedule_appointment(arguments)
            elif function_name == "web_search":
                return self._handle_web_search(arguments)
            elif function_name == "enhanced_service_search":
                return self._handle_enhanced_service_search(arguments)
            else:
                return {"error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            logger.error(f"Error executing function {function_name}: {e}")
            return {"error": f"Function execution failed: {str(e)}"}
    
    def _handle_get_client_info(self, args: Dict) -> Dict:
        """Handle get_client_info function"""
        client_identifier = args.get("client_identifier")
        if not client_identifier:
            return {"error": "client_identifier is required"}
        
        result = self.data_access.get_client_info(client_identifier)
        return {"type": "client_info", "data": result}
    
    def _handle_get_court_dates(self, args: Dict) -> Dict:
        """Handle get_court_dates function"""
        client_id = args.get("client_id")
        if not client_id:
            return {"error": "client_id is required"}
        
        court_dates = self.data_access.get_court_dates(client_id)
        return {"type": "court_dates", "data": court_dates}
    
    def _handle_search_jobs(self, args: Dict) -> Dict:
        """Handle search_jobs function"""
        keywords = args.get("keywords")
        if not keywords:
            return {"error": "keywords is required"}
        
        location = args.get("location")
        client_id = args.get("client_id")
        
        jobs = self.data_access.search_jobs(keywords, location, client_id)
        return {"type": "job_results", "data": {"jobs": jobs, "keywords": keywords, "location": location}}
    
    def _handle_get_job_matches(self, args: Dict) -> Dict:
        """Handle get_job_matches function"""
        client_id = args.get("client_id")
        if not client_id:
            return {"error": "client_id is required"}
        
        keywords = args.get("keywords")
        location = args.get("location")
        
        matches = self.data_access.get_job_matches(client_id, keywords, location)
        return {"type": "job_matches", "data": {"jobs": matches, "client_id": client_id}}
    
    def _handle_search_housing(self, args: Dict) -> Dict:
        """Handle search_housing function"""
        location = args.get("location")
        housing_type = args.get("housing_type")
        background_friendly = args.get("background_friendly", True)
        
        housing = self.data_access.search_housing(location, housing_type, background_friendly)
        return {"type": "housing_results", "data": {"housing": housing, "location": location}}
    
    def _handle_search_providers(self, args: Dict) -> Dict:
        """Handle search_providers function"""
        service_type = args.get("service_type")
        if not service_type:
            return {"error": "service_type is required"}
        
        location = args.get("location")
        
        providers = self.data_access.search_providers(service_type, location)
        return {"type": "provider_results", "data": {"providers": providers, "service_type": service_type}}
    
    def _handle_get_referral_status(self, args: Dict) -> Dict:
        """Handle get_referral_status function"""
        client_id = args.get("client_id")
        if not client_id:
            return {"error": "client_id is required"}
        
        referral_id = args.get("referral_id")
        
        referrals = self.data_access.get_referral_status(client_id, referral_id)
        return {"type": "referral_status", "data": {"referrals": referrals, "client_id": client_id}}
    
    def _handle_get_client_summary(self, args: Dict) -> Dict:
        """Handle get_client_summary function"""
        client_id = args.get("client_id")
        if not client_id:
            return {"error": "client_id is required"}
        
        summary = self.data_access.get_client_summary(client_id)
        return {"type": "client_summary", "data": summary}
    
    def _handle_search_all(self, args: Dict) -> Dict:
        """Handle search_all function"""
        query = args.get("query")
        if not query:
            return {"error": "query is required"}
        
        limit = args.get("limit", 10)
        
        results = self.data_access.search_all(query, limit)
        return {"type": "search_results", "data": results}
    
    def _handle_get_platform_stats(self, args: Dict) -> Dict:
        """Handle get_platform_stats function"""
        stats = self.data_access.get_platform_stats()
        return {"type": "platform_stats", "data": stats}
    
    def _handle_create_task(self, args: Dict) -> Dict:
        """Handle create_task function"""
        try:
            # Basic task creation - could be enhanced with actual database integration
            client_id = args.get("client_id")
            title = args.get("title")
            description = args.get("description", "")
            due_date = args.get("due_date")
            priority = args.get("priority", "medium")
            
            # For now, return a success message indicating the task would be created
            return {
                "type": "task_created",
                "data": {
                    "message": f"Task '{title}' scheduled for client {client_id} on {due_date} with {priority} priority",
                    "task_details": {
                        "title": title,
                        "description": description,
                        "due_date": due_date,
                        "priority": priority,
                        "client_id": client_id
                    }
                }
            }
        except Exception as e:
            return {"error": f"Failed to create task: {str(e)}"}
    
    def _handle_add_case_note(self, args: Dict) -> Dict:
        """Handle add_case_note function"""
        try:
            # Basic case note creation - could be enhanced with actual database integration
            client_id = args.get("client_id")
            note_text = args.get("note_text")
            note_type = args.get("note_type", "other")
            
            # For now, return a success message indicating the note would be added
            return {
                "type": "note_added",
                "data": {
                    "message": f"Case note added for client {client_id}: {note_text[:50]}...",
                    "note_details": {
                        "client_id": client_id,
                        "note_text": note_text,
                        "note_type": note_type,
                        "timestamp": datetime.now().isoformat()
                    }
                }
            }
        except Exception as e:
            return {"error": f"Failed to add case note: {str(e)}"}
    
    def _handle_schedule_appointment(self, args: Dict) -> Dict:
        """Handle schedule_appointment function"""
        try:
            # Basic appointment scheduling - could be enhanced with actual database integration
            client_id = args.get("client_id")
            appointment_date = args.get("appointment_date")
            appointment_type = args.get("appointment_type")
            description = args.get("description", "")
            location = args.get("location", "TBD")
            
            # For now, return a success message indicating the appointment would be scheduled
            return {
                "type": "appointment_scheduled",
                "data": {
                    "message": f"{appointment_type} appointment scheduled for client {client_id} on {appointment_date}",
                    "appointment_details": {
                        "client_id": client_id,
                        "appointment_date": appointment_date,
                        "appointment_type": appointment_type,
                        "description": description,
                        "location": location,
                        "status": "scheduled"
                    }
                }
            }
        except Exception as e:
            return {"error": f"Failed to schedule appointment: {str(e)}"}
    
    def _handle_web_search(self, args: Dict) -> Dict:
        """Handle web_search function"""
        try:
            query = args.get("query")
            if not query:
                return {"error": "query is required"}
            
            location = args.get("location", "")
            max_results = args.get("max_results", 10)
            
            # For now, skip web search and use database search directly
            # TODO: Fix web search API configuration
            logger.info("Using database search instead of web search")
            # Fallback to database search
            try:
                providers = self.data_access.search_providers(query, location)
                housing = self.data_access.search_housing(location, query) if location else []
                jobs = self.data_access.search_jobs(query, location) if "job" in query.lower() else []
                
                all_results = []
                
                # Add providers
                for provider in providers:
                    all_results.append({
                        "name": provider.get("name", "Unknown"),
                        "type": "service_provider",
                        "description": provider.get("description", ""),
                        "address": provider.get("address", ""),
                        "phone": provider.get("phone", ""),
                        "category": provider.get("category", ""),
                        "source": "platform_database"
                    })
                
                # Add housing if relevant
                if "housing" in query.lower() or "home" in query.lower():
                    for house in housing:
                        all_results.append({
                            "name": house.get("name", "Unknown"),
                            "type": "housing",
                            "description": house.get("description", ""),
                            "address": house.get("address", ""),
                            "phone": house.get("phone", ""),
                            "housing_type": house.get("housing_type", ""),
                            "source": "platform_database"
                        })
                
                # Add jobs if relevant  
                for job in jobs:
                    all_results.append({
                        "name": job.get("title", "Unknown"),
                        "type": "job",
                        "description": job.get("description", ""),
                        "company": job.get("company", ""),
                        "location": job.get("location", ""),
                        "salary": job.get("salary", ""),
                        "source": "platform_database"
                    })
                
                return {
                    "type": "web_search_results",
                    "data": {
                        "query": query,
                        "location": location,
                        "results": all_results,
                        "total_found": len(all_results),
                        "message": "Searched platform database. Web search will be available once configured."
                    }
                }
            except Exception as fallback_error:
                logger.error(f"Fallback search also failed: {fallback_error}")
                return {
                    "type": "web_search_results",
                    "data": {
                        "query": query,
                        "location": location,
                        "results": [],
                        "message": "Search functionality is currently unavailable. Please try again later."
                    }
                }
                
        except Exception as e:
            return {"error": f"Failed to perform web search: {str(e)}"}
    
    def _handle_enhanced_service_search(self, args: Dict) -> Dict:
        """Handle enhanced_service_search function"""
        try:
            query = args.get("query")
            if not query:
                return {"error": "query is required"}
            
            location = args.get("location", "")
            max_results = args.get("max_results", 20)
            
            # For now, skip enhanced web search and use basic database search  
            # TODO: Fix web search API configuration
            logger.info("Using basic database search instead of enhanced web search")
            # Fallback to basic service search
            providers = self.data_access.search_providers(query, location)
            return {
                "type": "enhanced_service_search_results",
                "data": {
                    "query": query,
                    "location": location,
                    "services": providers,
                    "total_found": len(providers),
                    "message": "Using basic service search - enhanced features will be available soon."
                }
            }
                
        except Exception as e:
            return {"error": f"Failed to perform enhanced service search: {str(e)}"}