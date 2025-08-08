"""
Database service layer for Case Management Suite using SQLAlchemy ORM
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.exc import SQLAlchemyError

from .models import Appointment, SavedJob, Resume, Client, User, AppointmentStatus, JobStatus, Task, TaskPriority, TaskStatus
from .session import get_session

logger = logging.getLogger(__name__)

class AppointmentService:
    """Service for appointment operations"""
    
    @staticmethod
    def create_appointment(appointment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new appointment"""
        try:
            with get_session() as session:
                # Convert date string to datetime if needed
                appointment_date = appointment_data.get('appointment_date')
                if isinstance(appointment_date, str):
                    appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d')
                
                appointment = Appointment(
                    id=appointment_data.get('appointment_id'),
                    client_id=appointment_data.get('client_id'),
                    case_manager_id=appointment_data.get('case_manager_id'),
                    appointment_type=appointment_data.get('appointment_type', 'General'),
                    provider_name=appointment_data.get('provider_name', ''),
                    appointment_date=appointment_date,
                    appointment_time=appointment_data.get('appointment_time', '09:00'),
                    location=appointment_data.get('location', ''),
                    notes=appointment_data.get('notes', ''),
                    status=AppointmentStatus.SCHEDULED
                )
                
                session.add(appointment)
                session.commit()
                session.refresh(appointment)
                
                return {
                    'appointment_id': appointment.id,
                    'client_id': appointment.client_id,
                    'appointment_date': appointment.appointment_date.isoformat() if appointment.appointment_date else None,
                    'appointment_time': appointment.appointment_time,
                    'appointment_type': appointment.appointment_type,
                    'status': appointment.status.value,
                    'created_at': appointment.created_at.isoformat() if appointment.created_at else None
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error creating appointment: {e}")
            raise
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            raise
    
    @staticmethod
    def get_appointments(client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get appointments, optionally filtered by client_id"""
        try:
            with get_session() as session:
                query = session.query(Appointment).join(Client, Appointment.client_id == Client.id)
                
                if client_id:
                    query = query.filter(Appointment.client_id == client_id)
                
                appointments = query.order_by(desc(Appointment.appointment_date)).all()
                
                result = []
                for appointment in appointments:
                    result.append({
                        'appointment_id': appointment.id,
                        'client_id': appointment.client_id,
                        'client_name': f"{appointment.client.first_name} {appointment.client.last_name}" if appointment.client else "Unknown",
                        'appointment_date': appointment.appointment_date.strftime('%Y-%m-%d') if appointment.appointment_date else None,
                        'appointment_time': appointment.appointment_time,
                        'appointment_type': appointment.appointment_type,
                        'status': appointment.status.value,
                        'notes': appointment.notes
                    })
                
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting appointments: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting appointments: {e}")
            raise

class JobService:
    """Service for job operations"""
    
    @staticmethod
    def save_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a job for a client"""
        try:
            with get_session() as session:
                # Convert date strings to datetime if needed
                posted_date = job_data.get('posted_date')
                if isinstance(posted_date, str):
                    posted_date = datetime.strptime(posted_date, '%Y-%m-%d')
                
                saved_job = SavedJob(
                    id=job_data.get('saved_job_id'),
                    client_id=job_data.get('client_id'),
                    job_title=job_data.get('job_title'),
                    company=job_data.get('company'),
                    location=job_data.get('location'),
                    salary=job_data.get('salary'),
                    job_type=job_data.get('job_type'),
                    background_friendly=job_data.get('background_friendly', False),
                    description=job_data.get('description'),
                    posted_date=posted_date,
                    source=job_data.get('source'),
                    status=JobStatus.SAVED
                )
                
                session.add(saved_job)
                session.commit()
                session.refresh(saved_job)
                
                return {
                    'saved_job_id': saved_job.id,
                    'client_id': saved_job.client_id,
                    'job_title': saved_job.job_title,
                    'company': saved_job.company,
                    'location': saved_job.location,
                    'salary': saved_job.salary,
                    'saved_date': saved_job.saved_date.isoformat() if saved_job.saved_date else None,
                    'status': saved_job.status.value
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving job: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving job: {e}")
            raise
    
    @staticmethod
    def get_saved_jobs(client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get saved jobs, optionally filtered by client_id"""
        try:
            with get_session() as session:
                query = session.query(SavedJob).join(Client, SavedJob.client_id == Client.id)
                
                if client_id:
                    query = query.filter(SavedJob.client_id == client_id)
                
                saved_jobs = query.order_by(desc(SavedJob.saved_date)).all()
                
                result = []
                for job in saved_jobs:
                    result.append({
                        'saved_job_id': job.id,
                        'client_id': job.client_id,
                        'job_title': job.job_title,
                        'company': job.company,
                        'location': job.location,
                        'salary': job.salary,
                        'saved_date': job.saved_date.strftime('%Y-%m-%d') if job.saved_date else None,
                        'status': job.status.value,
                        'application_date': job.application_date.strftime('%Y-%m-%d') if job.application_date else None
                    })
                
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting saved jobs: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting saved jobs: {e}")
            raise

class ResumeService:
    """Service for resume operations"""
    
    @staticmethod
    def save_resume(resume_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save a resume for a client"""
        try:
            with get_session() as session:
                resume = Resume(
                    id=resume_data.get('resume_id'),
                    client_id=resume_data.get('client_id'),
                    resume_name=resume_data.get('resume_name', 'My Resume'),
                    resume_data=resume_data.get('resume_data', {}),
                    job_context=resume_data.get('job_context', ''),
                    template_used=resume_data.get('template_used'),
                    file_path=resume_data.get('file_path'),
                    download_url=resume_data.get('download_url')
                )
                
                session.add(resume)
                session.commit()
                session.refresh(resume)
                
                return {
                    'resume_id': resume.id,
                    'client_id': resume.client_id,
                    'resume_name': resume.resume_name,
                    'resume_data': resume.resume_data,
                    'job_context': resume.job_context,
                    'created_date': resume.created_at.isoformat() if resume.created_at else None,
                    'file_path': resume.file_path
                }
                
        except SQLAlchemyError as e:
            logger.error(f"Database error saving resume: {e}")
            raise
        except Exception as e:
            logger.error(f"Error saving resume: {e}")
            raise
    
    @staticmethod
    def get_resumes(client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get resumes, optionally filtered by client_id"""
        try:
            with get_session() as session:
                query = session.query(Resume).join(Client, Resume.client_id == Client.id)
                
                if client_id:
                    query = query.filter(Resume.client_id == client_id)
                
                resumes = query.order_by(desc(Resume.created_at)).all()
                
                result = []
                for resume in resumes:
                    result.append({
                        'resume_id': resume.id,
                        'client_id': resume.client_id,
                        'client_name': f"{resume.client.first_name} {resume.client.last_name}" if resume.client else "Unknown",
                        'resume_name': resume.resume_name,
                        'job_context': resume.job_context,
                        'created_date': resume.created_at.strftime('%Y-%m-%d') if resume.created_at else None,
                        'file_path': resume.file_path,
                        'download_url': resume.download_url
                    })
                
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting resumes: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting resumes: {e}")
            raise

class SmartDashboardService:
    """Service for smart dashboard operations"""
    
    @staticmethod
    def get_smart_dashboard(case_manager_id: str) -> Dict[str, Any]:
        """Get smart dashboard with prioritized tasks for case manager"""
        try:
            with get_session() as session:
                today = datetime.now().date()
                tomorrow = today + timedelta(days=1)
                next_week = today + timedelta(days=7)
                
                # Get tasks for the case manager
                tasks_query = session.query(Task).join(Client, Task.client_id == Client.id)
                
                # Filter by assigned case manager if needed
                # For now, get all tasks since we don't have case manager assignment in Task model
                
                # Get today's tasks (due today or overdue)
                today_tasks = tasks_query.filter(
                    and_(
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                        or_(
                            Task.due_date <= today,
                            Task.priority == TaskPriority.URGENT
                        )
                    )
                ).order_by(Task.priority, Task.due_date).limit(5).all()
                
                # Get tomorrow's tasks
                tomorrow_tasks = tasks_query.filter(
                    and_(
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                        Task.due_date == tomorrow
                    )
                ).order_by(Task.priority).limit(3).all()
                
                # Get next week's tasks
                next_week_tasks = tasks_query.filter(
                    and_(
                        Task.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                        and_(
                            Task.due_date > tomorrow,
                            Task.due_date <= next_week
                        )
                    )
                ).order_by(Task.priority, Task.due_date).limit(3).all()
                
                # Convert tasks to dashboard format
                def convert_task_to_dashboard(task):
                    return {
                        'task_id': task.id,
                        'client_name': f"{task.client.first_name} {task.client.last_name}" if task.client else "Unknown",
                        'task_title': task.title,
                        'priority': task.priority.value.title(),
                        'estimated_duration': 30,  # Default duration
                        'due_time': '09:00',  # Default time
                        'due_date': task.due_date.strftime('%Y-%m-%d') if task.due_date else None,
                        'status': task.status.value.title()
                    }
                
                today_tasks_data = [convert_task_to_dashboard(task) for task in today_tasks]
                tomorrow_tasks_data = [convert_task_to_dashboard(task) for task in tomorrow_tasks]
                next_week_tasks_data = [convert_task_to_dashboard(task) for task in next_week_tasks]
                
                # Calculate workload summary
                total_tasks = len(today_tasks) + len(tomorrow_tasks) + len(next_week_tasks)
                urgent_tasks = len([t for t in today_tasks if t.priority == TaskPriority.URGENT])
                today_minutes = len(today_tasks) * 30  # 30 minutes per task
                tomorrow_minutes = len(tomorrow_tasks) * 60  # 60 minutes per task
                week_hours = (len(today_tasks) + len(tomorrow_tasks) + len(next_week_tasks)) * 0.5  # 30 min average
                
                dashboard_data = {
                    'case_manager_id': case_manager_id,
                    'generated_at': datetime.now().isoformat(),
                    'today_tasks': today_tasks_data,
                    'tomorrow_tasks': tomorrow_tasks_data,
                    'next_week_tasks': next_week_tasks_data,
                    'workload_summary': {
                        'total_tasks': total_tasks,
                        'urgent_tasks': urgent_tasks,
                        'today_estimated_minutes': today_minutes,
                        'tomorrow_estimated_minutes': tomorrow_minutes,
                        'week_estimated_hours': week_hours
                    }
                }
                
                return dashboard_data
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting smart dashboard: {e}")
            raise
        except Exception as e:
            logger.error(f"Error getting smart dashboard: {e}")
            raise
