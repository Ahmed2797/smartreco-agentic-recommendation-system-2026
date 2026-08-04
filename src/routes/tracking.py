from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import json

from src.database.db import get_db
from src.database import models

router = APIRouter(
    prefix="/tracking",
    tags=["Event Tracking"]
)


# =====================================
# Pydantic Schemas
# =====================================
class EventPayload(BaseModel):
    user_id: int
    event_type: str
    event_data: Optional[str] = None
    product_id: Optional[int] = None


# =====================================
# 1. Capture Tracking Event Endpoint
# =====================================
@router.post(
    "/event",
    status_code=status.HTTP_201_CREATED
)
async def capture_event(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Captures user behavior events sent via fetch() or navigator.sendBeacon().
    Supports both Standard JSON application/json and Beacon Blob payloads.
    """
    try:
        # Handle payload parsing (Supports both normal fetch and sendBeacon)
        body_bytes = await request.body()
        if not body_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty event body payload received."
            )

        payload_dict = json.loads(body_bytes.decode("utf-8"))
        event_data = EventPayload(**payload_dict)

        # 1. Verify user exists
        user = db.query(models.User).filter(models.User.id == event_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {event_data.user_id} not found."
            )

        # 2. Store event in UserActivity / Event tracking database table
        new_event = models.UserActivity(
            user_id=event_data.user_id,
            event_type=event_data.event_type,
            event_data=event_data.event_data,
            product_id=event_data.product_id,
            created_at=datetime.utcnow()
        )

        db.add(new_event)
        db.commit()
        db.refresh(new_event)

        return {
            "status": "success",
            "message": "Event logged successfully",
            "event_id": new_event.id,
            "event_type": new_event.event_type
        }

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid JSON format in payload."
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record tracking event: {str(e)}"
        )


# =====================================
# 2. Get User Activity History (Optional Utility)
# =====================================
@router.get(
    "/history/{user_id}",
    status_code=status.HTTP_200_OK
)
def get_user_activity_history(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Retrieve recent activity history for a specific user.
    """
    activities = (
        db.query(models.UserActivity)
        .filter(models.UserActivity.user_id == user_id)
        .order_by(models.UserActivity.created_at.desc())
        .limit(limit)
        .all()
    )

    return {
        "user_id": user_id,
        "count": len(activities),
        "history": activities
    }