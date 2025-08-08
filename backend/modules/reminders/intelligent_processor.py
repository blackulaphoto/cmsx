#!/usr/bin/env python3
"""
Intelligent Task Processor - Core AI-powered task generation and sequencing
Generates intelligent task sequences for case management processes
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import uuid
import json

logger = logging.getLogger(__name__)

class IntelligentTaskProcessor:
    """
    AI-powered task processor that generates intelligent task sequences
    for complex case management processes like disability claims, housing search, etc.
    """
    
    def __init__(self):
        """Initialize the intelligent task processor"""
        self.process_templates = self._load_process_templates()
        self.current_date = datetime.now()
        
    def _load_process_templates(self) -> Dict[str, Any]:
        """Load predefined process templates for different case types"""
        return {
            "disability_claim": {
                "name": "Disability Claim Process",
                "estimated_weeks": 6,
                "phases": [
                    {
                        "phase": "Documentation Gathering",
                        "week": 1,
                        "tasks": [
                            {
                                "title": "Get state ID/documents",
                                "description": "Help client obtain required identification documents",
                                "estimated_minutes": 60,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Request medical records from primary care physician",
                                "description": "Contact client's primary care doctor for medical records",
                                "estimated_minutes": 30,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Request medical records from specialists",
                                "description": "Contact all specialist doctors for comprehensive medical history",
                                "estimated_minutes": 45,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Contact previous hospitals for records",
                                "description": "Obtain hospital records from previous admissions",
                                "estimated_minutes": 30,
                                "priority": "Medium",
                                "dependencies": []
                            }
                        ]
                    },
                    {
                        "phase": "Application Preparation",
                        "week": 2,
                        "tasks": [
                            {
                                "title": "Follow up on pending medical records",
                                "description": "Check status of all requested medical records",
                                "estimated_minutes": 30,
                                "priority": "High",
                                "dependencies": ["Request medical records from primary care physician"]
                            },
                            {
                                "title": "Complete disability application form",
                                "description": "Fill out comprehensive disability application with client",
                                "estimated_minutes": 90,
                                "priority": "High",
                                "dependencies": ["Get state ID/documents"]
                            },
                            {
                                "title": "Gather supporting documents",
                                "description": "Collect all additional supporting documentation",
                                "estimated_minutes": 45,
                                "priority": "Medium",
                                "dependencies": []
                            }
                        ]
                    },
                    {
                        "phase": "Submission and Follow-up",
                        "week": 3,
                        "tasks": [
                            {
                                "title": "Submit disability claim",
                                "description": "Submit completed application and all supporting documents",
                                "estimated_minutes": 60,
                                "priority": "High",
                                "dependencies": ["Complete disability application form"]
                            },
                            {
                                "title": "Get confirmation receipt",
                                "description": "Obtain confirmation of claim submission",
                                "estimated_minutes": 15,
                                "priority": "High",
                                "dependencies": ["Submit disability claim"]
                            },
                            {
                                "title": "Start housing search (SSI-eligible)",
                                "description": "Begin searching for SSI-eligible housing options",
                                "estimated_minutes": 60,
                                "priority": "Medium",
                                "dependencies": []
                            }
                        ]
                    }
                ]
            },
            "housing_search": {
                "name": "Housing Search Process",
                "estimated_weeks": 3,
                "phases": [
                    {
                        "phase": "Research and Preparation",
                        "week": 1,
                        "tasks": [
                            {
                                "title": "Research available housing options",
                                "description": "Identify suitable housing options in client's area",
                                "estimated_minutes": 60,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Gather required documents",
                                "description": "Collect ID, income verification, references, etc.",
                                "estimated_minutes": 45,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Check credit and background requirements",
                                "description": "Review client's credit and background status",
                                "estimated_minutes": 30,
                                "priority": "Medium",
                                "dependencies": []
                            }
                        ]
                    },
                    {
                        "phase": "Applications and Viewings",
                        "week": 2,
                        "tasks": [
                            {
                                "title": "Submit housing applications",
                                "description": "Apply to multiple suitable housing options",
                                "estimated_minutes": 90,
                                "priority": "High",
                                "dependencies": ["Gather required documents"]
                            },
                            {
                                "title": "Schedule property viewings",
                                "description": "Arrange to view available properties with client",
                                "estimated_minutes": 60,
                                "priority": "High",
                                "dependencies": ["Research available housing options"]
                            },
                            {
                                "title": "Follow up on application status",
                                "description": "Check status of submitted applications",
                                "estimated_minutes": 30,
                                "priority": "Medium",
                                "dependencies": ["Submit housing applications"]
                            }
                        ]
                    },
                    {
                        "phase": "Decision and Move-in",
                        "week": 3,
                        "tasks": [
                            {
                                "title": "Review housing offers",
                                "description": "Evaluate any housing offers with client",
                                "estimated_minutes": 45,
                                "priority": "High",
                                "dependencies": ["Follow up on application status"]
                            },
                            {
                                "title": "Prepare for move-in",
                                "description": "Help client prepare for moving process",
                                "estimated_minutes": 60,
                                "priority": "Medium",
                                "dependencies": ["Review housing offers"]
                            }
                        ]
                    }
                ]
            },
            "employment_prep": {
                "name": "Employment Preparation Process",
                "estimated_weeks": 2,
                "phases": [
                    {
                        "phase": "Skills Assessment and Resume",
                        "week": 1,
                        "tasks": [
                            {
                                "title": "Conduct skills assessment",
                                "description": "Evaluate client's skills and work experience",
                                "estimated_minutes": 60,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Create or update resume",
                                "description": "Develop professional resume highlighting client's strengths",
                                "estimated_minutes": 90,
                                "priority": "High",
                                "dependencies": ["Conduct skills assessment"]
                            },
                            {
                                "title": "Job search training",
                                "description": "Teach effective job search strategies",
                                "estimated_minutes": 60,
                                "priority": "Medium",
                                "dependencies": []
                            },
                            {
                                "title": "Interview preparation",
                                "description": "Practice interview skills and techniques",
                                "estimated_minutes": 75,
                                "priority": "Medium",
                                "dependencies": []
                            }
                        ]
                    },
                    {
                        "phase": "Job Applications and Follow-up",
                        "week": 2,
                        "tasks": [
                            {
                                "title": "Apply to suitable positions",
                                "description": "Submit applications to 10+ relevant job openings",
                                "estimated_minutes": 120,
                                "priority": "High",
                                "dependencies": ["Create or update resume"]
                            },
                            {
                                "title": "Follow up on applications",
                                "description": "Contact employers about submitted applications",
                                "estimated_minutes": 45,
                                "priority": "Medium",
                                "dependencies": ["Apply to suitable positions"]
                            },
                            {
                                "title": "Schedule interviews",
                                "description": "Coordinate interview appointments",
                                "estimated_minutes": 30,
                                "priority": "High",
                                "dependencies": ["Follow up on applications"]
                            }
                        ]
                    }
                ]
            },
            "benefits_enrollment": {
                "name": "Benefits Enrollment Process",
                "estimated_weeks": 2,
                "phases": [
                    {
                        "phase": "Benefits Assessment",
                        "week": 1,
                        "tasks": [
                            {
                                "title": "Assess eligibility for benefits programs",
                                "description": "Determine which benefits client qualifies for",
                                "estimated_minutes": 60,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Gather required documentation",
                                "description": "Collect all necessary documents for applications",
                                "estimated_minutes": 45,
                                "priority": "High",
                                "dependencies": []
                            },
                            {
                                "title": "Schedule benefits appointments",
                                "description": "Book appointments at relevant agencies",
                                "estimated_minutes": 30,
                                "priority": "Medium",
                                "dependencies": ["Assess eligibility for benefits programs"]
                            }
                        ]
                    },
                    {
                        "phase": "Applications and Follow-up",
                        "week": 2,
                        "tasks": [
                            {
                                "title": "Complete benefits applications",
                                "description": "Fill out and submit all benefit applications",
                                "estimated_minutes": 90,
                                "priority": "High",
                                "dependencies": ["Gather required documentation"]
                            },
                            {
                                "title": "Attend benefits interviews",
                                "description": "Accompany client to benefits interviews",
                                "estimated_minutes": 120,
                                "priority": "High",
                                "dependencies": ["Schedule benefits appointments"]
                            },
                            {
                                "title": "Follow up on application status",
                                "description": "Check status of all submitted applications",
                                "estimated_minutes": 30,
                                "priority": "Medium",
                                "dependencies": ["Complete benefits applications"]
                            }
                        ]
                    }
                ]
            }
        }
    
    def generate_process_tasks(self, client_id: str, process_type: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        Generate intelligent task sequence for a specific process type
        
        Args:
            client_id: Unique identifier for the client
            process_type: Type of process (disability_claim, housing_search, etc.)
            context: Additional context for task customization
            
        Returns:
            List of generated tasks with timing and dependencies
        """
        try:
            if process_type not in self.process_templates:
                logger.warning(f"Unknown process type: {process_type}")
                return self._generate_generic_tasks(client_id, process_type, context)
            
            template = self.process_templates[process_type]
            generated_tasks = []
            
            # Generate tasks from template
            for phase in template["phases"]:
                phase_start_date = self.current_date + timedelta(weeks=phase["week"] - 1)
                
                for task_template in phase["tasks"]:
                    task = {
                        "task_id": str(uuid.uuid4()),
                        "client_id": client_id,
                        "process_type": process_type,
                        "phase": phase["phase"],
                        "title": task_template["title"],
                        "description": task_template["description"],
                        "estimated_minutes": task_template["estimated_minutes"],
                        "priority": task_template["priority"],
                        "dependencies": task_template["dependencies"],
                        "scheduled_date": phase_start_date.isoformat(),
                        "status": "Pending",
                        "created_at": self.current_date.isoformat(),
                        "context": context or {}
                    }
                    
                    # Apply context-based customizations
                    if context:
                        task = self._customize_task_with_context(task, context)
                    
                    generated_tasks.append(task)
            
            logger.info(f"Generated {len(generated_tasks)} tasks for {process_type} process for client {client_id}")
            return generated_tasks
            
        except Exception as e:
            logger.error(f"Error generating process tasks: {e}")
            return self._generate_generic_tasks(client_id, process_type, context)
    
    def _customize_task_with_context(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply context-based customizations to tasks"""
        try:
            # Adjust priority based on urgency
            if context.get("urgency") == "high":
                if task["priority"] == "Medium":
                    task["priority"] = "High"
                task["estimated_minutes"] = int(task["estimated_minutes"] * 0.8)  # Faster execution for urgent cases
            
            # Adjust timing based on client availability
            if context.get("client_availability") == "limited":
                task["estimated_minutes"] = int(task["estimated_minutes"] * 1.2)  # More time needed
            
            # Add special notes for complex cases
            if context.get("complexity") == "high":
                task["description"] += " (Complex case - may require additional time and resources)"
                task["estimated_minutes"] = int(task["estimated_minutes"] * 1.3)
            
            return task
            
        except Exception as e:
            logger.error(f"Error customizing task with context: {e}")
            return task
    
    def _generate_generic_tasks(self, client_id: str, process_type: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Generate generic tasks for unknown process types"""
        generic_tasks = [
            {
                "task_id": str(uuid.uuid4()),
                "client_id": client_id,
                "process_type": process_type,
                "phase": "Initial Assessment",
                "title": f"Initial assessment for {process_type}",
                "description": f"Conduct initial assessment and planning for {process_type} process",
                "estimated_minutes": 60,
                "priority": "High",
                "dependencies": [],
                "scheduled_date": self.current_date.isoformat(),
                "status": "Pending",
                "created_at": self.current_date.isoformat(),
                "context": context or {}
            },
            {
                "task_id": str(uuid.uuid4()),
                "client_id": client_id,
                "process_type": process_type,
                "phase": "Documentation",
                "title": f"Gather documentation for {process_type}",
                "description": f"Collect all necessary documents and information for {process_type}",
                "estimated_minutes": 45,
                "priority": "High",
                "dependencies": [f"Initial assessment for {process_type}"],
                "scheduled_date": (self.current_date + timedelta(days=1)).isoformat(),
                "status": "Pending",
                "created_at": self.current_date.isoformat(),
                "context": context or {}
            },
            {
                "task_id": str(uuid.uuid4()),
                "client_id": client_id,
                "process_type": process_type,
                "phase": "Follow-up",
                "title": f"Follow-up on {process_type} progress",
                "description": f"Check progress and next steps for {process_type}",
                "estimated_minutes": 30,
                "priority": "Medium",
                "dependencies": [f"Gather documentation for {process_type}"],
                "scheduled_date": (self.current_date + timedelta(days=7)).isoformat(),
                "status": "Pending",
                "created_at": self.current_date.isoformat(),
                "context": context or {}
            }
        ]
        
        logger.info(f"Generated {len(generic_tasks)} generic tasks for unknown process type: {process_type}")
        return generic_tasks
    
    def get_available_process_types(self) -> List[str]:
        """Get list of available process types"""
        return list(self.process_templates.keys())
    
    def get_process_info(self, process_type: str) -> Dict[str, Any]:
        """Get information about a specific process type"""
        if process_type in self.process_templates:
            template = self.process_templates[process_type]
            return {
                "name": template["name"],
                "estimated_weeks": template["estimated_weeks"],
                "total_phases": len(template["phases"]),
                "total_tasks": sum(len(phase["tasks"]) for phase in template["phases"]),
                "estimated_total_minutes": sum(
                    sum(task["estimated_minutes"] for task in phase["tasks"]) 
                    for phase in template["phases"]
                )
            }
        return {}
    
    def validate_task_dependencies(self, tasks: List[Dict[str, Any]]) -> bool:
        """Validate that task dependencies are properly structured"""
        try:
            task_titles = {task["title"] for task in tasks}
            
            for task in tasks:
                for dependency in task.get("dependencies", []):
                    if dependency not in task_titles:
                        logger.warning(f"Task '{task['title']}' has unresolved dependency: '{dependency}'")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating task dependencies: {e}")
            return False

