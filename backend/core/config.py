"""
Core configuration settings for Case Management Suite
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class AISettings(BaseSettings):
    """AI service configuration"""
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "2000"))
    timeout: float = 30.0
    max_retries: int = 3

class DatabaseSettings(BaseSettings):
    """Database configuration"""
    url: str = os.getenv("DATABASE_URL", "sqlite:///databases/case_management.db")

class Settings(BaseSettings):
    """Main application settings"""
    ai: AISettings = AISettings()
    database: DatabaseSettings = DatabaseSettings()
    
    # API settings
    api_title: str = "Case Management Suite"
    api_version: str = "2.0.0"
    api_description: str = "Comprehensive case management platform for reentry services"
    
    # Security
    secret_key: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # External APIs
    google_api_key: str = os.getenv("GOOGLE_API_KEY", "")
    google_cse_id: str = os.getenv("GOOGLE_CSE_ID", "")
    
    # File paths
    static_dir: str = "static"
    templates_dir: str = "templates"
    logs_dir: str = "logs"
    uploads_dir: str = "uploads"
    
    # Debug settings
    debug: bool = os.getenv("DEBUG", "False").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))

# Global settings instance
settings = Settings() 