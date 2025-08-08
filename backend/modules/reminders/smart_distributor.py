#!/usr/bin/env python3
"""
Intelligent Task Distribution Engine
Smart workload management and process automation
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import json
from .process_models import ProcessDatabase, ProcessTemplate, ClientProcess, DistributedTask
from .models import ReminderDatabase
from .engine import IntelligentReminderEngine

logger = logging.getLogger(__name__)

class SmartTaskDistributor:
    """
    Intelligent task distribution engine that:
    - Breaks down complex processes into daily tasks
    - Distributes tasks optimally across the week
    - Manages capacity and prevents overload
    - Sequences tasks based on dependencies
    """
    
    def __init__(self, reminder_db: ReminderDatabase):
        self.reminder_db = reminder_db
        self.process_db = ProcessDatabase(reminder_db)
        self.reminder_engine = IntelligentReminderEngine(reminder_db)
        
        # Daily capacity limits
        self.daily_capacity = {
            'phone_calls': 8,          # Max calls per day
            'appointments': 3,         # Max in-person meetings
            'paperwork': 5,           # Max forms/applications
            'follow_ups': 10,         # Quick check-ins
            'research': 3,            # Research tasks
            'crisis_time': 2,         # Emergency buffer hours
            'total_hours': 6          # Total productive hours per day
        }
        
        # Task type time estimates (minutes)
        self.task_time_estimates = {
            'phone_call': 30,
            'appointment': 90,
            'paperwork': 60,
            'follow_up': 15,
            'research': 45,
            'crisis_response': 60
        }
        
        # Priority scoring weights
        self.priority_weights = {
            'urgency': 40,            # How urgent is the task
            'impact': 30,             # Impact on client outcome
            'deadline': 20,           # Proximity to deadline
            'dependencies': 10        # Blocks other tasks
        }
    
    def generate_weekly_task_plan(self, case_manager_id: str) -> Dict[str, Any]:
        """
        Generate intelligent weekly task distribution plan
        """
        try:
            # Get all clients for case manager
            clients = self._get_case_manager_clients(case_manager_id)
            
            # Get all active processes
            all_processes = []
            for client in clients:
                processes = self.process_db.get_client_processes(client['client_id'])
                all_processes.extend(processes)
            
            # Generate tasks from processes
            generated_tasks = self._generate_tasks_from_processes(all_processes)
            
            # Get existing contact reminders
            reminder_tasks = self._get_reminder_tasks(case_manager_id)
            
            # Combine all tasks
            all_tasks = generated_tasks + reminder_tasks
            
            # Prioritize and score tasks
            prioritized_tasks = self._prioritize_tasks(all_tasks)
            
            # Distribute across week
            weekly_plan = self._distribute_tasks_across_week(prioritized_tasks)
            
            # Calculate capacity metrics
            capacity_metrics = self._calculate_capacity_metrics(weekly_plan)
            
            return {
                'case_manager_id': case_manager_id,
                'generated_at': datetime.now().isoformat(),
                'weekly_plan': weekly_plan,
                'capacity_metrics': capacity_metrics,
                'total_tasks': len(all_tasks),
                'process_count': len(all_processes),
                'recommendations': self._generate_weekly_recommendations(weekly_plan, capacity_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly task plan: {e}")
            return {'error': str(e)}
    
    def start_client_process(self, client_id: str, case_manager_id: str, process_type: str, 
                           priority_level: str = 'Medium', context: Dict[str, Any] = None) -> str:
        """
        Start a new process for a client and generate distributed tasks
        """
        try:
            # Get process template
            template = self.process_db.get_process_template(f"{process_type}_process")
            if not template:
                raise ValueError(f"Process template not found: {process_type}")
            
            # Create client process
            process = ClientProcess(
                client_id=client_id,
                case_manager_id=case_manager_id,
                template_id=template.template_id,
                process_type=process_type,
                process_name=template.process_name,
                priority_level=priority_level,
                target_completion_date=(datetime.now() + timedelta(weeks=template.estimated_weeks)).isoformat(),
                context=context or {}
            )
            
            # Save process
            self.process_db.save_client_process(process)
            
            # Generate and distribute tasks
            self._generate_and_distribute_process_tasks(process, template)
            
            logger.info(f"Started process {process_type} for client {client_id}")
            return process.process_id
            
        except Exception as e:
            logger.error(f"Error starting client process: {e}")
            raise
    
    def get_daily_focus_plan(self, case_manager_id: str, date: str = None) -> Dict[str, Any]:
        """
        Get today's focus plan with intelligent task prioritization
        """
        try:
            if not date:
                date = datetime.now().strftime('%Y-%m-%d')
            
            # Get tasks for the day
            daily_tasks = self.process_db.get_daily_tasks(case_manager_id, date)
            
            # Group by priority and type
            task_groups = self._group_tasks_by_priority(daily_tasks)
            
            # Calculate time budget
            time_budget = self._calculate_daily_time_budget(daily_tasks)
            
            # Generate focus recommendations
            focus_recommendations = self._generate_daily_focus_recommendations(task_groups, time_budget)
            
            return {
                'case_manager_id': case_manager_id,
                'date': date,
                'generated_at': datetime.now().isoformat(),
                'task_groups': task_groups,
                'time_budget': time_budget,
                'focus_recommendations': focus_recommendations,
                'capacity_status': self._assess_daily_capacity(daily_tasks)
            }
            
        except Exception as e:
            logger.error(f"Error generating daily focus plan: {e}")
            return {'error': str(e)}
    
    def _generate_tasks_from_processes(self, processes: List[ClientProcess]) -> List[Dict[str, Any]]:
        """Generate tasks from active processes"""
        tasks = []
        
        for process in processes:
            # Get process template
            template = self.process_db.get_process_template(process.template_id)
            if not template:
                continue
            
            # Calculate current week
            started_date = datetime.fromisoformat(process.started_date)
            current_week = ((datetime.now() - started_date).days // 7) + 1
            
            # Get tasks for current week
            week_key = f"week_{current_week}"
            if week_key not in template.steps:
                # Check for day-based steps for urgent processes
                day_key = f"day_{current_week}"
                if day_key in template.steps:
                    week_key = day_key
                else:
                    continue
            
            week_tasks = template.steps[week_key]
            
            for task_template in week_tasks:
                task = {
                    'client_id': process.client_id,
                    'case_manager_id': process.case_manager_id,
                    'process_id': process.process_id,
                    'task_type': task_template.get('type', 'phone_call'),
                    'task_description': task_template['task'],
                    'estimated_minutes': task_template.get('minutes', 30),
                    'priority_level': process.priority_level,
                    'urgency_score': self._calculate_urgency_score(process, task_template),
                    'process_context': {
                        'process_name': process.process_name,
                        'process_type': process.process_type,
                        'current_week': current_week,
                        'completion_percentage': process.completion_percentage
                    }
                }
                tasks.append(task)
        
        return tasks
    
    def _get_reminder_tasks(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get tasks from reminder system"""
        tasks = []
        
        # Get dashboard data for reminders
        dashboard = self.reminder_engine.generate_morning_dashboard(case_manager_id)
        
        if 'error' in dashboard:
            return tasks
        
        # Convert urgent items to tasks
        for item in dashboard.get('urgent_items', []):
            task = {
                'client_id': item['client_id'],
                'case_manager_id': case_manager_id,
                'process_id': None,
                'task_type': 'contact' if item['type'] == 'contact' else 'appointment',
                'task_description': item['message'],
                'estimated_minutes': 45 if item['type'] == 'contact' else 30,
                'priority_level': 'Critical',
                'urgency_score': 100,
                'reminder_context': {
                    'type': item['type'],
                    'action': item['action'],
                    'days_overdue': item.get('days_overdue', 0)
                }
            }
            tasks.append(task)
        
        # Convert today items to tasks
        for item in dashboard.get('today_items', []):
            task = {
                'client_id': item['client_id'],
                'case_manager_id': case_manager_id,
                'process_id': None,
                'task_type': 'contact' if item['type'] == 'contact' else 'appointment',
                'task_description': item['message'],
                'estimated_minutes': 30,
                'priority_level': 'High',
                'urgency_score': 80,
                'reminder_context': {
                    'type': item['type'],
                    'action': item['action']
                }
            }
            tasks.append(task)
        
        return tasks
    
    def _prioritize_tasks(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize tasks using intelligent scoring"""
        
        for task in tasks:
            # Calculate priority score
            urgency_score = task.get('urgency_score', 50)
            impact_score = self._calculate_impact_score(task)
            deadline_score = self._calculate_deadline_score(task)
            dependency_score = self._calculate_dependency_score(task)
            
            # Weighted total score
            total_score = (
                urgency_score * (self.priority_weights['urgency'] / 100) +
                impact_score * (self.priority_weights['impact'] / 100) +
                deadline_score * (self.priority_weights['deadline'] / 100) +
                dependency_score * (self.priority_weights['dependencies'] / 100)
            )
            
            task['priority_score'] = total_score
            task['impact_score'] = impact_score
            task['deadline_score'] = deadline_score
            task['dependency_score'] = dependency_score
        
        # Sort by priority score
        return sorted(tasks, key=lambda x: x['priority_score'], reverse=True)
    
    def _distribute_tasks_across_week(self, tasks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Distribute tasks across the week based on capacity"""
        
        # Initialize weekly plan
        weekly_plan = {}
        current_date = datetime.now().date()
        
        for i in range(7):  # 7 days
            date = current_date + timedelta(days=i)
            day_name = date.strftime('%A').lower()
            weekly_plan[day_name] = {
                'date': date.strftime('%Y-%m-%d'),
                'tasks': [],
                'capacity_used': {
                    'phone_calls': 0,
                    'appointments': 0,
                    'paperwork': 0,
                    'follow_ups': 0,
                    'research': 0,
                    'total_minutes': 0
                }
            }
        
        # Distribute tasks
        for task in tasks:
            # Find best day for this task
            best_day = self._find_best_day_for_task(task, weekly_plan)
            
            if best_day:
                # Add task to that day
                weekly_plan[best_day]['tasks'].append(task)
                
                # Update capacity
                task_type = task['task_type']
                if task_type in weekly_plan[best_day]['capacity_used']:
                    weekly_plan[best_day]['capacity_used'][task_type] += 1
                
                weekly_plan[best_day]['capacity_used']['total_minutes'] += task['estimated_minutes']
                
                # Create and save distributed task
                distributed_task = DistributedTask(
                    case_manager_id=task['case_manager_id'],
                    client_id=task['client_id'],
                    process_id=task.get('process_id'),
                    task_type=task['task_type'],
                    task_description=task['task_description'],
                    scheduled_date=weekly_plan[best_day]['date'],
                    estimated_minutes=task['estimated_minutes'],
                    priority_level=task['priority_level'],
                    urgency_score=task['urgency_score']
                )
                self.process_db.save_distributed_task(distributed_task)
        
        return weekly_plan
    
    def _find_best_day_for_task(self, task: Dict[str, Any], weekly_plan: Dict[str, Dict]) -> Optional[str]:
        """Find the best day to schedule a task"""
        
        task_type = task['task_type']
        task_minutes = task['estimated_minutes']
        task_priority = task['priority_level']
        
        # Check each day's capacity
        for day_name, day_data in weekly_plan.items():
            capacity = day_data['capacity_used']
            
            # Check if day has capacity for this task type
            if task_type in capacity:
                if capacity[task_type] >= self.daily_capacity.get(task_type, 999):
                    continue
            
            # Check total time capacity
            total_minutes = capacity['total_minutes'] + task_minutes
            if total_minutes > (self.daily_capacity['total_hours'] * 60):
                continue
            
            # This day has capacity
            return day_name
        
        # If no day has capacity, find the day with least load
        least_loaded_day = min(weekly_plan.keys(), 
                             key=lambda d: weekly_plan[d]['capacity_used']['total_minutes'])
        return least_loaded_day
    
    def _calculate_urgency_score(self, process: ClientProcess, task_template: Dict[str, Any]) -> int:
        """Calculate urgency score for a task"""
        base_score = 50
        
        # Increase score based on process priority
        if process.priority_level == 'Critical':
            base_score += 40
        elif process.priority_level == 'High':
            base_score += 20
        elif process.priority_level == 'Medium':
            base_score += 0
        else:
            base_score -= 10
        
        # Increase score based on time sensitivity
        started_date = datetime.fromisoformat(process.started_date)
        days_since_start = (datetime.now() - started_date).days
        
        if days_since_start > 7:  # Process is overdue
            base_score += 20
        
        # Increase score based on urgency factor
        base_score = int(base_score * process.urgency_factor)
        
        return min(100, max(0, base_score))
    
    def _calculate_impact_score(self, task: Dict[str, Any]) -> int:
        """Calculate impact score for a task"""
        base_score = 50
        
        # High impact task types
        high_impact_types = ['paperwork', 'appointment']
        if task['task_type'] in high_impact_types:
            base_score += 20
        
        # Tasks that unblock other tasks
        if 'blocks' in task.get('task_description', '').lower():
            base_score += 15
        
        # Critical client processes
        if task.get('priority_level') == 'Critical':
            base_score += 25
        
        return min(100, max(0, base_score))
    
    def _calculate_deadline_score(self, task: Dict[str, Any]) -> int:
        """Calculate deadline proximity score"""
        base_score = 50
        
        # Check if task has deadline indicators
        description = task.get('task_description', '').lower()
        if 'urgent' in description or 'asap' in description:
            base_score += 30
        elif 'today' in description:
            base_score += 40
        elif 'this week' in description:
            base_score += 10
        
        return min(100, max(0, base_score))
    
    def _calculate_dependency_score(self, task: Dict[str, Any]) -> int:
        """Calculate dependency score (how many tasks this blocks)"""
        base_score = 50
        
        # Tasks that are prerequisites for others
        description = task.get('task_description', '').lower()
        if 'get' in description and ('id' in description or 'document' in description):
            base_score += 20  # Getting documents unblocks other tasks
        
        if 'records' in description:
            base_score += 15  # Medical records needed for applications
        
        return min(100, max(0, base_score))
    
    def _group_tasks_by_priority(self, tasks: List[DistributedTask]) -> Dict[str, List[Dict[str, Any]]]:
        """Group tasks by priority level"""
        groups = {
            'urgent': [],
            'high_priority': [],
            'scheduled': [],
            'optional': []
        }
        
        for task in tasks:
            task_dict = task.to_dict()
            
            if task.priority_level == 'Critical' or task.urgency_score >= 90:
                groups['urgent'].append(task_dict)
            elif task.priority_level == 'High' or task.urgency_score >= 70:
                groups['high_priority'].append(task_dict)
            elif task.priority_level == 'Medium' or task.urgency_score >= 40:
                groups['scheduled'].append(task_dict)
            else:
                groups['optional'].append(task_dict)
        
        return groups
    
    def _calculate_daily_time_budget(self, tasks: List[DistributedTask]) -> Dict[str, Any]:
        """Calculate daily time budget and usage"""
        total_estimated_minutes = sum(task.estimated_minutes for task in tasks)
        available_minutes = self.daily_capacity['total_hours'] * 60
        
        return {
            'total_estimated_minutes': total_estimated_minutes,
            'available_minutes': available_minutes,
            'utilization_percentage': (total_estimated_minutes / available_minutes) * 100,
            'overload': total_estimated_minutes > available_minutes,
            'buffer_minutes': available_minutes - total_estimated_minutes
        }
    
    def _generate_daily_focus_recommendations(self, task_groups: Dict[str, List], time_budget: Dict[str, Any]) -> List[str]:
        """Generate focus recommendations for the day"""
        recommendations = []
        
        urgent_count = len(task_groups['urgent'])
        high_priority_count = len(task_groups['high_priority'])
        
        if urgent_count > 0:
            recommendations.append(f"🔥 IMMEDIATE PRIORITY: Handle {urgent_count} urgent items first")
        
        if high_priority_count > 0:
            recommendations.append(f"📋 HIGH PRIORITY: Complete {high_priority_count} important tasks")
        
        if time_budget['overload']:
            recommendations.append("⚠️ OVERLOAD WARNING: Consider rescheduling non-critical tasks")
        elif time_budget['buffer_minutes'] > 60:
            recommendations.append("✅ CAPACITY AVAILABLE: Good day to tackle optional tasks")
        
        # Task sequencing recommendations
        if urgent_count > 0:
            recommendations.append("🎯 SEQUENCE: Urgent tasks → High priority → Scheduled tasks")
        
        return recommendations
    
    def _assess_daily_capacity(self, tasks: List[DistributedTask]) -> Dict[str, Any]:
        """Assess daily capacity utilization"""
        capacity_used = {
            'phone_calls': 0,
            'appointments': 0,
            'paperwork': 0,
            'follow_ups': 0,
            'research': 0
        }
        
        for task in tasks:
            task_type = task.task_type
            if task_type in capacity_used:
                capacity_used[task_type] += 1
        
        capacity_status = {}
        for task_type, used in capacity_used.items():
            max_capacity = self.daily_capacity.get(task_type, 999)
            capacity_status[task_type] = {
                'used': used,
                'max': max_capacity,
                'utilization': (used / max_capacity) * 100 if max_capacity > 0 else 0,
                'overload': used > max_capacity
            }
        
        return capacity_status
    
    def _calculate_capacity_metrics(self, weekly_plan: Dict[str, Dict]) -> Dict[str, Any]:
        """Calculate weekly capacity metrics"""
        metrics = {
            'total_tasks': 0,
            'total_minutes': 0,
            'daily_averages': {},
            'overload_days': [],
            'underutilized_days': []
        }
        
        for day_name, day_data in weekly_plan.items():
            task_count = len(day_data['tasks'])
            total_minutes = day_data['capacity_used']['total_minutes']
            
            metrics['total_tasks'] += task_count
            metrics['total_minutes'] += total_minutes
            
            # Check for overload
            if total_minutes > (self.daily_capacity['total_hours'] * 60):
                metrics['overload_days'].append(day_name)
            elif total_minutes < (self.daily_capacity['total_hours'] * 60 * 0.5):
                metrics['underutilized_days'].append(day_name)
        
        # Calculate daily averages
        num_days = len(weekly_plan)
        if num_days > 0:
            metrics['daily_averages'] = {
                'tasks_per_day': metrics['total_tasks'] / num_days,
                'minutes_per_day': metrics['total_minutes'] / num_days,
                'utilization_percentage': (metrics['total_minutes'] / (num_days * self.daily_capacity['total_hours'] * 60)) * 100
            }
        
        return metrics
    
    def _generate_weekly_recommendations(self, weekly_plan: Dict[str, Dict], capacity_metrics: Dict[str, Any]) -> List[str]:
        """Generate weekly recommendations"""
        recommendations = []
        
        # Overload warnings
        if capacity_metrics['overload_days']:
            recommendations.append(f"⚠️ OVERLOAD: {', '.join(capacity_metrics['overload_days'])} are overloaded")
        
        # Underutilization opportunities
        if capacity_metrics['underutilized_days']:
            recommendations.append(f"📈 OPPORTUNITY: {', '.join(capacity_metrics['underutilized_days'])} have extra capacity")
        
        # Overall utilization
        avg_utilization = capacity_metrics['daily_averages'].get('utilization_percentage', 0)
        if avg_utilization > 90:
            recommendations.append("🔥 HIGH UTILIZATION: Consider delegating or deferring non-critical tasks")
        elif avg_utilization < 60:
            recommendations.append("✅ GOOD CAPACITY: Excellent opportunity for proactive client work")
        
        return recommendations
    
    def _generate_and_distribute_process_tasks(self, process: ClientProcess, template: ProcessTemplate):
        """Generate and distribute tasks for a process"""
        # This would generate tasks for the entire process timeline
        # For now, we'll focus on the current week
        current_week = 1
        week_key = f"week_{current_week}"
        
        if week_key in template.steps:
            week_tasks = template.steps[week_key]
            
            for i, task_template in enumerate(week_tasks):
                # Schedule tasks across the week
                scheduled_date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
                
                task = DistributedTask(
                    case_manager_id=process.case_manager_id,
                    client_id=process.client_id,
                    process_id=process.process_id,
                    task_type=task_template.get('type', 'phone_call'),
                    task_description=task_template['task'],
                    scheduled_date=scheduled_date,
                    estimated_minutes=task_template.get('minutes', 30),
                    priority_level=process.priority_level,
                    urgency_score=self._calculate_urgency_score(process, task_template)
                )
                
                self.process_db.save_distributed_task(task)
    
    def _get_case_manager_clients(self, case_manager_id: str) -> List[Dict[str, Any]]:
        """Get clients for case manager from database"""
        return self.reminder_db.get_clients_for_case_manager(case_manager_id)