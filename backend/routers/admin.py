from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any
import logging
from services.db_client import get_all_applications, update_application_status

logger = logging.getLogger("didi.admin")
router = APIRouter()

@router.get("/applications")
def list_applications():
    """
    Retrieves all applications submitted by users.
    """
    try:
        apps = get_all_applications()
        # Sort by most recent first based on created_at
        sorted_apps = sorted(apps, key=lambda x: x.get("created_at", ""), reverse=True)
        return {"success": True, "data": sorted_apps}
    except Exception as e:
        logger.error(f"Failed to fetch applications: {e}")
        raise HTTPException(status_code=500, detail="Could not retrieve applications.")

@router.post("/applications/{application_id}/status")
def change_status(application_id: str, payload: Dict[str, str] = Body(...)):
    """
    Updates an application to APPROVED or REJECTED.
    Expects JSON body: {"status": "APPROVED", "reason": "Optional notes"}
    """
    status = payload.get("status")
    reason = payload.get("reason", "")
    
    if status not in ["APPROVED", "REJECTED", "PENDING"]:
        raise HTTPException(status_code=400, detail="Invalid status provided.")
        
    try:
        updated = update_application_status(application_id, status, reason)
        if updated:
            return {"success": True, "message": f"Successfully updated to {status}"}
        else:
            raise HTTPException(status_code=404, detail="Application not found.")
    except Exception as e:
        logger.error(f"Failed to update status for {application_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update database.")
