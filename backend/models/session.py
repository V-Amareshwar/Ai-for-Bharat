from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class User(BaseModel):
    """Represents a DidiGov user in the DynamoDB users table."""
    mobile_number: str
    created_at: str
    last_session: Optional[str] = None
    language: str = "en"

class ChatMessage(BaseModel):
    """An individual message inside a conversation."""
    role: str      # 'user' or 'assistant'
    content: str
    timestamp: str

class ConversationSession(BaseModel):
    """
    Represents an ongoing conversation in the DynamoDB conversations table.
    Contains the rolling history of messages, dialog extraction state, and extracted form data.
    """
    session_id: str
    user_id: str
    state: str = "idle"
    messages: List[ChatMessage] = Field(default_factory=list)
    created_at: str
    form_data: Dict[str, Any] = Field(default_factory=dict)

class DidiApplication(BaseModel):
    """
    Represents a submitted government scheme application in the DynamoDB applications table.
    """
    application_id: str
    scheme_id: str
    user_id: str
    data: Dict[str, Any]
    status: str
    created_at: str
