import sys
import os
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database import models
from src.routes.auth import get_current_user
from src.pipeline.retrieval_pipeline import retrieve_relevant_products_pipeline
from src.prompt.recommendation_prompt import get_persuasive_recommendation_prompt
from src.chatmodel.mesh_client import mesh_client
from src.agent.recommendation_agent import generate_and_save_user_recommendation

# =====================================
# RAG + Mesh API Execution Pipeline
# =====================================
def execute_recommendation_pipeline(user_id: int, db: Session) -> Optional[models.Recommendation]:
    """
    Executes the complete RAG Recommendation Pipeline:
    1. Fetches recent user events (UserActivity).
    2. Runs vector semantic retrieval for relevant products in Pinecone.
    3. Generates Mesh API LLM persuasive narrative.
    4. Saves and returns the Recommendation record.
    """
    # 1. Fetch recent activity events from DB
    ActivityModel = getattr(models, "UserActivity", getattr(models, "ActivityEvent", None))
    if not ActivityModel:
        print("⚠️ Neither UserActivity nor ActivityEvent model found.")
        return None

    events = (
        db.query(ActivityModel)
        .filter(ActivityModel.user_id == user_id)
        .order_by(ActivityModel.created_at.desc())
        .limit(8)
        .all()
    )

    if not events:
        print(f"⚠️ No activity events found for User {user_id}.")
        return None

    # Chronological ordering (Oldest to Newest)
    events.reverse()
    actions_summary = "; ".join([
        f"{e.event_type}: {getattr(e, 'event_data', '') or getattr(e, 'description', '')}" 
        for e in events
    ])

    # 2. Semantic Retrieval via Vector Pipeline
    matched_ids = retrieve_relevant_products_pipeline(actions_summary)
    if not matched_ids:
        print(f"⚠️ No matching products returned from vector pipeline for User {user_id}.")
        return None

    # Fetch products and preserve vector relevance ordering
    products_db = db.query(models.Product).filter(models.Product.id.in_(matched_ids)).all()
    product_map = {p.id: p for p in products_db}
    
    ordered_products = [product_map[p_id] for p_id in matched_ids if p_id in product_map]
    product_titles = [p.title for p in ordered_products]

    # 3. Dynamic Prompt Generation
    prompt = get_persuasive_recommendation_prompt(actions_summary, product_titles)

    # 4. LLM Execution via Mesh API
    try:
        response = mesh_client.chat.completions.create(
            model="openai/gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert AI product recommender assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )
        narrative = response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ Mesh LLM API Error: {e}")
        narrative = f"Based on your recent interest in {product_titles[0] if product_titles else 'our courses'}, we highly recommend these selections."

    # 5. Save result in Recommendation DB
    try:
        rec = models.Recommendation(
            user_id=user_id,
            narrative=narrative,
            recommended_product_ids=matched_ids
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)
        
        print(f"✅ Recommendation pipeline completed & saved for User {user_id}")
        return rec

    except Exception as e:
        db.rollback()
        print(f"❌ Failed to save recommendation to Database: {e}")
        return None


# =====================================
# Response Schemas (Pydantic Models)
# =====================================
class RecommendationItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    price: float

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):
    user_id: int
    narrative: str
    count: int
    recommendations: List[RecommendationItem]


# =====================================
# FastAPI Recommendation Router
# =====================================
router = APIRouter(
    prefix="/api/recommendations",
    tags=["Recommendations"]
)


@router.get(
    "/me",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK
)
def get_my_recommendations(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Executes real-time RAG pipeline with Mesh API narrative for the authenticated user.
    """
    try:
        # rec_record = execute_recommendation_pipeline(user_id=current_user.id, db=db)
        rec_record = generate_and_save_user_recommendation(user_id=current_user.id, db=db)

        # Cold Start / Fallback if pipeline returns no products
        if not rec_record or not rec_record.recommended_product_ids:
            fallback_products = db.query(models.Product).limit(5).all()
            return {
                "user_id": current_user.id,
                "narrative": "Welcome to SmartReco AI! Here are our top featured courses to start your learning journey.",
                "count": len(fallback_products),
                "recommendations": fallback_products
            }

        products = (
            db.query(models.Product)
            .filter(models.Product.id.in_(rec_record.recommended_product_ids))
            .all()
        )

        return {
            "user_id": current_user.id,
            "narrative": rec_record.narrative,
            "count": len(products),
            "recommendations": products
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating Mesh recommendations: {str(e)}"
        )


@router.get(
    "/{user_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK
)
def get_recommendations_by_user_id(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Generate Mesh API recommendations for a specific user ID (Admin / Inspection).
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    try:
        rec_record = execute_recommendation_pipeline(user_id=user_id, db=db)

        if not rec_record or not rec_record.recommended_product_ids:
            fallback_products = db.query(models.Product).limit(5).all()
            return {
                "user_id": user_id,
                "narrative": "No activity history found. Displaying general course catalogue.",
                "count": len(fallback_products),
                "recommendations": fallback_products
            }

        products = (
            db.query(models.Product)
            .filter(models.Product.id.in_(rec_record.recommended_product_ids))
            .all()
        )

        return {
            "user_id": user_id,
            "narrative": rec_record.narrative,
            "count": len(products),
            "recommendations": products
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching user recommendations: {str(e)}"
        )