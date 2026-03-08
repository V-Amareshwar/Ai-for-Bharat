from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

from services.db_client import get_or_create_user, create_session

logger = logging.getLogger("didi.auth")
router = APIRouter()

class LoginRequest(BaseModel):
    mobile_number: str

class LoginResponse(BaseModel):
    session_id: str
    user_id: str
    is_new_user: bool

@router.post("/login", response_model=LoginResponse, summary="Mobile Number Login")
async def login(req: LoginRequest):
    """
    Identifies or creates a user by mobile number.
    Generates a new conversation session and returns the UUID `session_id`.
    This session_id should be stored in the frontend for future /chat/ requests.
    """
    mobile = req.mobile_number.strip()
    # Basic validation for an Indian 10-digit number structure, or anything >= 10
    if not mobile or len(mobile) < 10:
        raise HTTPException(status_code=400, detail="Invalid mobile number. Must be >= 10 digits.")
    
    try:
        user = get_or_create_user(mobile)
        is_new = user.last_session is None
        
        session = create_session(mobile)
        
        return LoginResponse(
            session_id=session.session_id,
            user_id=user.mobile_number,
            is_new_user=is_new
        )
    except Exception as e:
        logger.exception(f"Login failure for {mobile}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error connecting to user database.")
