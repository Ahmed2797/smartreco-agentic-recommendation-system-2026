import os
from typing import Optional, List
from fastapi import FastAPI, Request, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Database and Model Imports
from src.database.db import get_db
from src.database import models

# Router Imports
from src.routes import auth, admin, dashboard, products, recommendations, tracking

# LangGraph AI Agent Import (Ensure this matches your file location)
from src.agent.langgraph_agent import run_agentic_recommendation

app = FastAPI(title="SmartReco AI")

# Mount Static Files (for tracker.js, CSS, etc.)
if os.path.exists("frontend/static"):
    app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# Jinja2 Template Directory setup
templates = Jinja2Templates(directory="frontend/templates")

# Include Authentication Router
app.include_router(auth.router)
app.include_router(admin.router)

# app.include_router(dashboard.router)


# =========================================================
# 1. NEW: API Tracking Endpoint (Fixes the 404 POST /api/track)
# =========================================================

class TrackEventSchema(BaseModel):
    user_id: Optional[int] = None
    event_type: str
    description: Optional[str] = ""
    event_data: Optional[str] = ""
    product_id: Optional[int] = None
    timestamp: Optional[str] = None


# @app.post("/api/track", status_code=status.HTTP_200_OK)
# async def track_user_event(event: TrackEventSchema, db: Session = Depends(get_db)):
#     """
#     Receives behavioral events from tracker.js (e.g. search, product views, page loads)
#     and logs them so the AI Recommendation Agent can learn from user behavior.
#     """
#     print(f"--> [Tracker Event] Type: {event.event_type} | Desc: {event.description} | Product ID: {event.product_id}")
    
#     # Optional: Save event to database if you have an Event/Activity model
#     # new_event = models.UserActivity(event_type=event.event_type, description=event.description)
#     # db.add(new_event)
#     # db.commit()

#     return {"status": "success", "message": "Event logged successfully"}

@app.post("/api/track", status_code=status.HTTP_200_OK)
async def track_user_event(
    event: TrackEventSchema, 
    request: Request,
    db: Session = Depends(get_db)
):
    # Retrieve active user from cookie or request body
    user_id = request.cookies.get("user_id") or event.user_id

    if user_id:
        new_event = models.UserActivity(
            user_id=int(user_id),
            event_type=event.event_type,
            event_data= event.event_data or event.description,
            product_id=event.product_id
        )
        db.add(new_event)
        db.commit()
        return {"status": "success", "message": f"Logged event for user {user_id}"}

    return {"status": "ignored", "message": "No authenticated user"}


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    request: Request, 
    search: Optional[str] = None, 
    db: Session = Depends(get_db)
):
    # 1. Identify unique user from login cookie or session
    user_id = request.cookies.get("user_id")
    
    if not user_id:
        # Redirect to login if user isn't authenticated
        return RedirectResponse(url="/auth/login")

    user_id = int(user_id)
    current_user = db.query(models.User).filter(models.User.id == user_id).first()

    raw_events = db.query(models.UserActivity)\
    .filter(
        models.UserActivity.user_id == user_id,
        models.UserActivity.event_type.in_(["search", "product_click", "add_to_cart"])
    )\
    .order_by(models.UserActivity.created_at.desc())\
    .limit(10).all()

    user_events = [{"event_type": e.event_type, "description": e.event_data, "product_id": e.product_id}
        for e in raw_events
    ]

    # 3. Generate uniquely tailored recommendations for this email
    ai_recommendation = run_agentic_recommendation(
        user_id=user_id,
        user_events=user_events,
        search_query=search or ""
    )
    # rec_ids = ai_recommendation.get("recommended_product_ids", [])

    
    rec_ids = ai_recommendation.get("recommended_product_ids", [])
    # rec_ids = [int(p_id) for p_id in raw_ids if str(p_id).isdigit()]
    
    # 4. Load personalized products
    recommended_products = db.query(models.Product).filter(
        models.Product.id.in_(rec_ids)
    ).all() if rec_ids else []

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "search_term": search or "",
        "narrative": ai_recommendation.get("narrative", ""),
        "recommended_products": recommended_products,
        "products": db.query(models.Product).all()
    })


# Root Redirect
@app.get("/")
def root():
    return RedirectResponse(url="/dashboard")
### uvicorn main:app --reload
