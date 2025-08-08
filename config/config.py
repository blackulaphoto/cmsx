"""
Configuration settings for Case Management Suite
"""

import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # Database paths
    DATABASE_DIR = "databases"
    CASE_MANAGEMENT_DB = os.path.join(DATABASE_DIR, "case_management.db")
    HOUSING_DB = os.path.join(DATABASE_DIR, "housing_resources.db")
    SERVICES_DB = os.path.join(DATABASE_DIR, "services.db")
    RESUMES_DB = os.path.join(DATABASE_DIR, "resumes.db")
    BENEFITS_DB = os.path.join(DATABASE_DIR, "benefits_transport.db")
    
    # API Configuration
    API_TITLE = "Case Management Suite"
    API_VERSION = "2.0.0"
    API_DESCRIPTION = "Comprehensive case management platform for reentry services"
    
    # Security
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    # External APIs
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    
    # File paths
    STATIC_DIR = "static"
    TEMPLATES_DIR = "templates"
    LOGS_DIR = "logs"
    UPLOADS_DIR = "uploads"
    
    # Application settings
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

# Global config instance
config = Config() 