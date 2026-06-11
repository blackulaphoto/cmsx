"""
Resource Library Pydantic models for request/response validation.
"""
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class ResourceCreate(BaseModel):
    provider_name: str
    service_name: Optional[str] = None
    display_name: Optional[str] = None
    primary_category: Optional[str] = None
    secondary_categories: List[str] = Field(default_factory=list)
    pathways: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    services_offered: List[str] = Field(default_factory=list)
    people_served: List[str] = Field(default_factory=list)
    eligibility: List[str] = Field(default_factory=list)
    documents_required: List[Any] = Field(default_factory=list)
    cost: Optional[str] = None
    languages: List[str] = Field(default_factory=list)
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    locations: List[Any] = Field(default_factory=list)
    coverage_area: List[str] = Field(default_factory=list)
    cmsx_notes: Optional[str] = None
    verification_status: str = "needs_review"
    source: Optional[str] = None
    source_url: Optional[str] = None
    active: bool = True


class ResourceUpdate(BaseModel):
    provider_name: Optional[str] = None
    service_name: Optional[str] = None
    display_name: Optional[str] = None
    primary_category: Optional[str] = None
    secondary_categories: Optional[List[str]] = None
    pathways: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    services_offered: Optional[List[str]] = None
    people_served: Optional[List[str]] = None
    eligibility: Optional[List[str]] = None
    documents_required: Optional[List[Any]] = None
    cost: Optional[str] = None
    languages: Optional[List[str]] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    locations: Optional[List[Any]] = None
    coverage_area: Optional[List[str]] = None
    cmsx_notes: Optional[str] = None
    verification_status: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    active: Optional[bool] = None
