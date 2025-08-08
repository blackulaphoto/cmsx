"""
Core module for Case Management Suite
"""

from .config import settings
from .container import singleton

__all__ = ['settings', 'singleton'] 