import logging
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from botocore.exceptions import ClientError

from config import settings
from services.aws_clients import get_dynamodb_resource
from models.session import User, ConversationSession, ChatMessage, DidiApplication

logger = logging.getLogger("didi.db_client")

def get_or_create_user(mobile_number: str) -> User:
    """
    Looks up a user by mobile_number. 
    If they do not exist, creates a new record in DynamoDB.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_users_table)
    try:
        response = table.get_item(Key={"mobile_number": mobile_number})
        if "Item" in response:
            return User(**response["Item"])
        
        # Create new user
        now = datetime.utcnow().isoformat()
        user = User(mobile_number=mobile_number, created_at=now)
        table.put_item(Item=user.dict())
        logger.info(f"Created new user for mobile: {mobile_number}")
        return user
    except ClientError as e:
        logger.error(f"Error getting/creating user {mobile_number}: {e}")
        raise

def create_session(mobile_number: str) -> ConversationSession:
    """
    Initializes a new Conversation loop and stores it in DynamoDB.
    Also updates the User's last_session tracker.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_conversations_table)
    
    session_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    
    session = ConversationSession(
        session_id=session_id,
        user_id=mobile_number,
        created_at=now,
        state="idle",
        messages=[],
        form_data={}
    )
    
    # In DynamoDB, the conversations table uses session_id (HASH) and timestamp (RANGE).
    # To easily fetch/update the main metadata row of a session without knowing exactly when it was updated,
    # we enforce a static sort key of "metadata" for the session master object.
    item = session.dict()
    item["timestamp"] = "metadata"
    
    try:
        table.put_item(Item=item)
        logger.info(f"Created new session: {session_id} for user: {mobile_number}")
        
        # Update user's last session
        users_table = dynamodb.Table(settings.dynamodb_users_table)
        users_table.update_item(
            Key={"mobile_number": mobile_number},
            UpdateExpression="SET last_session = :s",
            ExpressionAttributeValues={":s": session_id}
        )
        return session
    except ClientError as e:
        logger.error(f"Error creating session: {e}")
        raise

def load_session(session_id: str) -> Optional[ConversationSession]:
    """
    Loads all data associated with a generated session_id.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_conversations_table)
    try:
        response = table.get_item(Key={"session_id": session_id, "timestamp": "metadata"})
        if "Item" in response:
            return ConversationSession(**response["Item"])
        return None
    except ClientError as e:
        logger.error(f"Error loading session {session_id}: {e}")
        raise

def update_session(session_id: str, state: str, messages: List[Dict[str, Any]], form_data: Dict[str, Any]):
    """
    Persists updates (new chat messages, new dialog state, and newly fulfilled forms) 
    down to the DynamoDB conversation record.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_conversations_table)
    try:
        table.update_item(
            Key={"session_id": session_id, "timestamp": "metadata"},
            UpdateExpression="SET #s = :state, messages = :msgs, form_data = :fdata",
            ExpressionAttributeNames={"#s": "state"},
            ExpressionAttributeValues={
                ":state": state,
                ":msgs": messages,
                ":fdata": form_data
            }
        )
        logger.info(f"Updated session state in DynamoDB: {session_id}")
    except ClientError as e:
        logger.error(f"Error updating session {session_id}: {e}")
        raise

def save_application(application: DidiApplication):
    """
    Saves a completed user application to the DynamoDB applications table.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_applications_table)
    try:
        table.put_item(Item=application.dict())
        logger.info(f"Saved application {application.application_id} for user {application.user_id}")
    except ClientError as e:
        logger.error(f"Error saving application {application.application_id}: {e}")
        raise

def get_all_applications() -> List[Dict[str, Any]]:
    """
    Scans the didi_applications table and returns all records.
    For production, this should use pagination or secondary index querying.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_applications_table)
    try:
        response = table.scan()
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"Error scanning applications: {e}")
        raise

def get_user_applications(user_id: str) -> List[Dict[str, Any]]:
    """
    Fetches all applications submitted by a specific user (mobile number).
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_applications_table)
    
    # We use scan with filter expression here because user_id isn't the partition key.
    # In production with large datasets, a GSI (Global Secondary Index) on user_id is required.
    from boto3.dynamodb.conditions import Attr
    try:
        response = table.scan(
            FilterExpression=Attr('user_id').eq(user_id)
        )
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"Error fetching applications for user {user_id}: {e}")
        return []

def update_application_status(application_id: str, status: str, reason: str = None) -> bool:
    """
    Updates the status (and optionally reason) of an application.
    """
    dynamodb = get_dynamodb_resource()
    table = dynamodb.Table(settings.dynamodb_applications_table)
    
    update_expr = "SET #s = :status"
    expr_attr_names = {"#s": "status"}
    expr_attr_values = {":status": status}
    
    if reason:
        update_expr += ", reason = :reason"
        expr_attr_values[":reason"] = reason

    try:
        table.update_item(
            Key={"application_id": application_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_attr_names,
            ExpressionAttributeValues=expr_attr_values
        )
        logger.info(f"Updated application {application_id} to status: {status}")
        return True
    except ClientError as e:
        logger.error(f"Error updating application {application_id}: {e}")
        raise
