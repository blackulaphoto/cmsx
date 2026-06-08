from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TopicCreate(BaseModel):
    title: str = Field(..., min_length=1)
    category: str = "General"
    description: Optional[str] = ""
    key_points: Optional[List[str]] = Field(default_factory=list)
    discussion_questions: Optional[List[str]] = Field(default_factory=list)
    activity: Optional[str] = ""
    writing_prompt: Optional[str] = ""
    facilitator_tips: Optional[str] = ""
    source: str = "custom"


class TopicUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    key_points: Optional[List[str]] = None
    discussion_questions: Optional[List[str]] = None
    activity: Optional[str] = None
    writing_prompt: Optional[str] = None
    facilitator_tips: Optional[str] = None


class AITopicGenerateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    group_length_minutes: int = 60
    population: str = "Adults in SUD/MH treatment"
    tone: str = "psychoeducational"
    additional_context: Optional[str] = ""


class PlaylistCreate(BaseModel):
    title: str = Field(..., min_length=1)
    youtube_playlist_url: str = Field(..., min_length=1)
    description: Optional[str] = ""
    category: str = "General"
    tags: Optional[List[str]] = Field(default_factory=list)


class PlaylistUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class VideoCreate(BaseModel):
    title: str = Field(..., min_length=1)
    youtube_url: str = Field(..., min_length=1)
    playlist_id: Optional[str] = None
    description: Optional[str] = ""
    category: str = "General"
    tags: Optional[List[str]] = Field(default_factory=list)


class VideoUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None


class SessionCreate(BaseModel):
    title: str = Field(..., min_length=1)
    topic_id: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    location: Optional[str] = ""
    group_type: str = "psychoeducation"
    playlist_ids: Optional[List[str]] = Field(default_factory=list)
    video_ids: Optional[List[str]] = Field(default_factory=list)
    facilitator_notes: Optional[str] = ""


class SessionUpdate(BaseModel):
    title: Optional[str] = None
    topic_id: Optional[str] = None
    scheduled_date: Optional[str] = None
    scheduled_time: Optional[str] = None
    location: Optional[str] = None
    group_type: Optional[str] = None
    status: Optional[str] = None
    playlist_ids: Optional[List[str]] = None
    video_ids: Optional[List[str]] = None
    facilitator_notes: Optional[str] = None


class AttendanceUpsert(BaseModel):
    client_id: str = Field(..., min_length=1)
    status: str = "present"
    participation_level: str = "moderate"


class NoteCreate(BaseModel):
    client_id: Optional[str] = None
    note_type: str = "group"
    content: str = ""
    ai_generated: bool = False
    quote_generated: bool = False
    reviewed: bool = False
    finalized: bool = False
    engagement_preset: Optional[str] = ""
    note_setting: str = "in-person"
    staff_quote: Optional[str] = ""


class NoteUpdate(BaseModel):
    content: Optional[str] = None
    note_type: Optional[str] = None
    reviewed: Optional[bool] = None
    finalized: Optional[bool] = None
    engagement_preset: Optional[str] = None
    note_setting: Optional[str] = None
    staff_quote: Optional[str] = None


class AttendeeNoteSpec(BaseModel):
    """Per-client note spec used in bulk generation."""
    client_id: str
    attendance_status: str = "present"
    participation_level: str = "moderate"
    engagement_preset: str = "moderate"
    staff_quote: Optional[str] = ""


class BulkGenerateRequest(BaseModel):
    """Request body for bulk individual-note generation."""
    note_setting: str = "in-person"
    allow_ai_quotes: bool = False
    attendees: List[AttendeeNoteSpec] = Field(default_factory=list)


class AIGroupNoteRequest(BaseModel):
    """Request for generating a single group summary or individual note."""
    note_type: str = "group"
    client_id: Optional[str] = None
    note_setting: str = "in-person"
    allow_ai_quotes: bool = False
    engagement_preset: Optional[str] = "moderate"
    staff_quote: Optional[str] = ""
    attendance_status: Optional[str] = "present"
    participation_level: Optional[str] = "moderate"
    context: Optional[Dict[str, Any]] = None
