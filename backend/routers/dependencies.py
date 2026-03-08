from fastapi import Header, HTTPException, Depends
import logging

from services.db_client import load_session
from models.session import ConversationSession

logger = logging.getLogger("didi.dependencies")

async def get_current_session(x_session_id: str = Header(None, description="The unique session ID from login")) -> ConversationSession:
    """
    FastAPI Dependency to load the current session state.
    Injects the ConversationSession object downstream if it exists in DynamoDB.
    """
    if not x_session_id:
        raise HTTPException(status_code=401, detail="Missing X-Session-Id header")
        
    session = load_session(x_session_id)
    if not session:
        logger.warning(f"Failed to find session data for: {x_session_id}")
        raise HTTPException(status_code=401, detail="Invalid or expired session")
        
    return session
