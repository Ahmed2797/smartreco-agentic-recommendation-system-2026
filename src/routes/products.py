from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database import models
from src.routes.recommendations import execute_recommendation_pipeline, get_my_recommendations

router = APIRouter(tags=["Products & Recommendations"])
templates = Jinja2Templates(directory="frontend/templates")

# ==========================================
# 1. Frontend UI Views (Jinja2 Templates)
# ==========================================

@router.get("/dashboard")
def render_dashboard(request: Request, db: Session = Depends(get_db)):
    products = db.query(models.Product).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "products": products})

@router.get("/admin")
def render_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/recommendations")
def render_recommendations(request: Request, db: Session = Depends(get_db)):
    user_id = 1
    recommendation = (
        db.query(models.Recommendation)
        .filter_by(user_id=user_id)
        .order_by(models.Recommendation.created_at.desc())
        .first()
    )
    
    recommended_products = []
    if recommendation and recommendation.recommended_product_ids:
        recommended_products = (
            db.query(models.Product)
            .filter(models.Product.id.in_(recommendation.recommended_product_ids))
            .all()
        )

    return templates.TemplateResponse("recommendations.html", {
        "request": request, 
        "recommendation": recommendation, 
        "recommended_products": recommended_products
    })


# ==========================================
# 2. JSON API Endpoints
# ==========================================

@router.get("/products/recommendations/{user_id}")
def get_user_recommendations(user_id: int, db: Session = Depends(get_db)):
    """Fetch recommendations for a specific user based on their activity events."""
    # rec = execute_recommendation_pipeline(user_id, db)
    rec = get_my_recommendations(user_id, db)
    
    if not rec:
        raise HTTPException(status_code=404, detail="No activity found to generate recommendations")
        
    return {
        "status": "success",
        "user_id": rec.user_id,
        "narrative": rec.narrative,
        "recommended_product_ids": rec.recommended_product_ids,
        "created_at": rec.created_at
    }