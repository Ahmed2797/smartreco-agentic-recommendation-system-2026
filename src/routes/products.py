from typing import List
from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database import models
from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import search_similar_products
from src.routes.recommendations import execute_recommendation_pipeline

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
# 2. Vector Search Helper Functions
# ==========================================

def get_similar_courses_by_product_id(product_id: int, db: Session, limit: int = 4) -> List[models.Product]:
    """
    Retrieves similar courses from Pinecone based on a clicked product's content.
    """
    # 1. Fetch clicked product from SQL DB
    target_product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not target_product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target product not found")

    # 2. Construct search context from product features
    context_text = f"{target_product.title} {target_product.category} {target_product.description or ''}"

    # 3. Generate embedding vector for the clicked product
    query_vector = get_text_embedding(context_text)

    # 4. Search Pinecone for top matches (fetching extra to exclude self-match)
    raw_matches = search_similar_products(query_vector, top_k=limit + 1)

    # 5. Extract IDs & scores, filtering out the clicked product itself
    score_map = {}
    ordered_ids = []

    for item in raw_matches:
        p_id = int(item["id"]) if isinstance(item, dict) else int(item)
        score = float(item.get("score", 0.85)) if isinstance(item, dict) else 0.85

        if p_id != product_id and p_id not in score_map:
            score_map[p_id] = round(score, 2)
            ordered_ids.append(p_id)
            if len(ordered_ids) == limit:
                break

    if not ordered_ids:
        # Fallback to same-category items if no vector matches found
        return (
            db.query(models.Product)
            .filter(models.Product.category == target_product.category, models.Product.id != product_id)
            .limit(limit)
            .all()
        )

    # 6. Query database and maintain vector relevance order
    products_db = db.query(models.Product).filter(models.Product.id.in_(ordered_ids)).all()
    product_dict = {p.id: p for p in products_db}
    
    similar_products = [product_dict[p_id] for p_id in ordered_ids if p_id in product_dict]

    # Attach score badge for UI rendering
    for prod in similar_products:
        prod.score = f"{int(score_map.get(prod.id, 0.85) * 100)}%"

    return similar_products


# ==========================================
# 3. JSON API Endpoints
# ==========================================

@router.get("/api/products/recommendations/{user_id}")
def get_user_recommendations(user_id: int, db: Session = Depends(get_db)):
    """Fetch recommendations for a specific user based on their activity events."""
    rec = execute_recommendation_pipeline(user_id, db)
    
    if not rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="No activity found to generate recommendations"
        )
        
    return {
        "status": "success",
        "user_id": rec.user_id,
        "narrative": rec.narrative,
        "recommended_product_ids": rec.recommended_product_ids,
        "created_at": rec.created_at
    }


@router.get("/api/products/{product_id}/similar", status_code=status.HTTP_200_OK)
def get_similar_products_endpoint(
    product_id: int,
    limit: int = 4,
    db: Session = Depends(get_db)
):
    """
    Triggered when a user clicks on Product #76 or any product card.
    Returns similar courses extracted from Pinecone.
    """
    similar_products = get_similar_courses_by_product_id(product_id=product_id, db=db, limit=limit)
    
    return {
        "clicked_product_id": product_id,
        "count": len(similar_products),
        "similar_courses": similar_products
    }