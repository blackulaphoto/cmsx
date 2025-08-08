"""
Database models for Case Management Suite using SQLAlchemy ORM
"""

from enum import Enum
from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class TaskPriority(str, Enum):
    """Task priority levels"""
    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class TaskStatus(str, Enum):
    """Task status levels"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AppointmentStatus(str, Enum):
    """Appointment status levels"""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class JobStatus(str, Enum):
    """Job application status levels"""
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFERED = "offered"
    REJECTED = "rejected"
    ACCEPTED = "accepted"

class Task(Base):
    """Task model using SQLAlchemy ORM"""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    due_date = Column(DateTime)
    priority = Column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(SQLEnum(TaskStatus), default=TaskStatus.PENDING)
    category = Column(String(100))
    assigned_to = Column(String, ForeignKey("users.id"))
    created_by = Column(String, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Enhanced reminders specific attributes
    task_type = Column(String(50))
    context_type = Column(String(50))
    context_id = Column(String)
    ai_generated = Column(Boolean, default=False)
    ai_priority_score = Column(Float, default=0.0)
    auto_generated = Column(Boolean, default=False)
    task_metadata = Column(Text)  # JSON string
    completed_date = Column(DateTime)
    updated_by = Column(String, ForeignKey("users.id"))
    
    # Relationships
    client = relationship("Client", back_populates="tasks")
    assigned_user = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tasks")
    created_user = relationship("User", foreign_keys=[created_by], back_populates="created_tasks")
    updated_user = relationship("User", foreign_keys=[updated_by])

class Client(Base):
    """Client model using SQLAlchemy ORM"""
    __tablename__ = "clients"
    
    id = Column(String, primary_key=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True)
    phone = Column(String(20))
    status = Column(String(50), default="active")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    tasks = relationship("Task", back_populates="client")
    appointments = relationship("Appointment", back_populates="client")
    saved_jobs = relationship("SavedJob", back_populates="client")
    resumes = relationship("Resume", back_populates="client")

class User(Base):
    """User model using SQLAlchemy ORM"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(50), default="user")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    assigned_tasks = relationship("Task", foreign_keys=[Task.assigned_to], back_populates="assigned_user")
    created_tasks = relationship("Task", foreign_keys=[Task.created_by], back_populates="created_user")

class Appointment(Base):
    """Appointment model using SQLAlchemy ORM"""
    __tablename__ = "appointments"
    
    id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    case_manager_id = Column(String, ForeignKey("users.id"))
    appointment_type = Column(String(100), nullable=False)
    provider_name = Column(String(255))
    appointment_date = Column(DateTime, nullable=False)
    appointment_time = Column(String(10))  # HH:MM format
    location = Column(String(255))
    notes = Column(Text)
    status = Column(SQLEnum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    client = relationship("Client", back_populates="appointments")
    case_manager = relationship("User", foreign_keys=[case_manager_id])

class SavedJob(Base):
    """Saved job model using SQLAlchemy ORM"""
    __tablename__ = "saved_jobs"
    
    id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    job_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255))
    salary = Column(String(100))
    job_type = Column(String(50))  # Full-time, Part-time, Contract, etc.
    background_friendly = Column(Boolean, default=False)
    description = Column(Text)
    posted_date = Column(DateTime)
    source = Column(String(100))  # Indeed, Craigslist, etc.
    status = Column(SQLEnum(JobStatus), default=JobStatus.SAVED)
    application_date = Column(DateTime)
    saved_date = Column(DateTime, default=datetime.now)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    client = relationship("Client", back_populates="saved_jobs")

class Resume(Base):
    """Resume model using SQLAlchemy ORM"""
    __tablename__ = "resumes"
    
    id = Column(String, primary_key=True)
    client_id = Column(String, ForeignKey("clients.id"), nullable=False)
    resume_name = Column(String(255), nullable=False)
    resume_data = Column(Text)  # JSON string containing resume content
    job_context = Column(String(500))  # Job description or context
    template_used = Column(String(100))
    file_path = Column(String(500))
    download_url = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    client = relationship("Client", back_populates="resumes") 