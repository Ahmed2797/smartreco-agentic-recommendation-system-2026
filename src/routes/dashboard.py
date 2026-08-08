from fastapi import APIRouter, Depends, Request, Query, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database import models
from src.agent.recommendation_agent import generate_and_save_user_recommendation

from src.routes.engine import RecommendationEngine
from src.routes.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["User Dashboard"])
templates = Jinja2Templates(directory="frontend/templates")


@router.get("", response_class=HTMLResponse)
def get_user_dashboard(
    request: Request,
    user_id: int = Query(default=1),
    db: Session = Depends(get_db)
):
    # 1. Fetch Current User
    current_user = db.query(models.User).filter(models.User.id == user_id).first()

    # 2. Run LangGraph Agent Recommendation
    agent_output = generate_and_save_user_recommendation(user_id=user_id, db=db)
    
    recommended_ids = agent_output.get("recommended_product_ids", [])
    narrative = agent_output.get("narrative", "")

    # 3. Fetch Product Objects for Recommended IDs
    recommended_products = (
        db.query(models.Product)
        .filter(models.Product.id.in_(recommended_ids))
        .all()
    ) if recommended_ids else []

    # Fallback if no specific recommendations found
    if not recommended_products:
        recommended_products = db.query(models.Product).limit(4).all()

    # Fetch All Products for General Catalog
    all_products = db.query(models.Product).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "products": all_products,
            "recommended_products": recommended_products,
            "ai_narrative": narrative  # Pass LLM generated narrative
        }
    )

# Usage inside your route handler (e.g. dashboard.py)


@router.get("/dashboard")
def dashboard(request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    
    # 1. Fast, zero-cost behavioral recommendations
    engine = RecommendationEngine(db=db)
    recommended_products = engine.generate_recommendations(user_id=current_user.id, limit=4)
    
    # 2. Attach calculated scores for your frontend UI badges
    recs = db.query(models.Recommendation).filter(models.Recommendation.user_id == current_user.id).all()
    score_map = {r.product_id: f"{int(r.score * 100)}%" for r in recs}
    
    for prod in recommended_products:
        prod.score = score_map.get(prod.id, "85%")

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "recommended_products": recommended_products
    })