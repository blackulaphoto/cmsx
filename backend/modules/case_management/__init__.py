"""
Case Management Module
Handles client intake, case management, and client data operations
"""

from .models import Client, CaseNote, Referral
from .routes import router
from .database import CaseManagementDatabase

__all__ = ['Client', 'CaseNote', 'Referral', 'router', 'CaseManagementDatabase']