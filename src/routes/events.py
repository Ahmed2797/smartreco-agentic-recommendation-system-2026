from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from src.database.db import get_db
from src.database import models
from src.routes.auth import get_current_user
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/events", tags=["Events"])

class EventCreate(BaseModel):
    event_type: str       # "view_page", "search_query", "product_click", "add_to_cart"
    event_data: str       # Search term, URL path, or action detail
    product_id: Optional[int] = None

@router.post("/log")
def log_user_event(
    event: EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    new_activity = models.UserActivity(
        user_id=current_user.id,
        product_id=event.product_id,
        event_type=event.event_type,
        event_data=event.event_data,
        created_at=datetime.utcnow()
    )
    try:
        db.add(new_activity)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to store event for user_id=%s", current_user.id)
        raise HTTPException(status_code=500, detail="Unable to log event")
    logger.info("Stored event type=%s for user_id=%s", event.event_type, current_user.id)
    return {"status": "success", "message": "Event logged"}
