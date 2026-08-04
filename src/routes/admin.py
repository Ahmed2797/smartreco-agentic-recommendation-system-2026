from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database.db import get_db
from src.database import models

router = APIRouter(
    prefix="/admin",
    tags=["Admin Dashboard"]
)

# Jinja2 templates directory configuration
templates = Jinja2Templates(directory="frontend/templates")


@router.get("", response_class=HTMLResponse)
@router.get("/dashboard", response_class=HTMLResponse)
def get_admin_dashboard(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Renders the Admin Dashboard with aggregated analytics, 
    system statistics, and recent activity logs.
    """
    # 1. Total Metrics Counters
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_products = db.query(func.count(models.Product.id)).scalar() or 0
    total_events = db.query(func.count(models.UserActivity.id)).scalar() or 0
    
    # Optional check for recommendations if Recommendation table exists
    total_recommendations = 0
    if hasattr(models, 'Recommendation'):
        total_recommendations = db.query(func.count(models.Recommendation.id)).scalar() or 0

    # 2. Query Event Counts grouped by event_type (For Chart.js)
    event_counts_query = (
        db.query(
            models.UserActivity.event_type,
            func.count(models.UserActivity.id).label("count")
        )
        .group_by(models.UserActivity.event_type)
        .all()
    )

    # Convert query result to Dictionary format
    event_counts = {event_type: count for event_type, count in event_counts_query}

    # 3. Fetch Recent Activity Stream (Latest 20 Events)
    recent_events = (
        db.query(models.UserActivity)
        .order_by(models.UserActivity.created_at.desc())
        .limit(20)
        .all()
    )

    # 4. Render admin.html with context data
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "total_users": total_users,
            "total_products": total_products,
            "total_events": total_events,
            "total_recommendations": total_recommendations,
            "event_counts": event_counts,
            "events": recent_events
        }
    )