from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database.db import get_db
from src.database import models
from src.services.recommendation_service import RecommendationEngine


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"]
)


# =====================================
# Response Schemas (Pydantic Models)
# =====================================
class RecommendationItem(BaseModel):
    product_id: int
    title: str
    category: str
    price: float
    score: float

class RecommendationResponse(BaseModel):
    user_id: int
    count: int
    recommendations: List[RecommendationItem]


# =====================================
# Recommendation Endpoint
# =====================================
@router.get(
    "/{user_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK
)
def get_recommendations(
    user_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """
    Get personalized product recommendations for a specific user.
    """
    # 1. Verify if user exists in the database
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    # 2. Generate recommendations using recommendation service
    try:
        recommendation_engine = RecommendationEngine(db)
        recommendations = recommendation_engine.generate_recommendations(
            user_id=user_id,
            limit=top_k
        )

        if not recommendations:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No recommendations found for this user."
            )

        return {
            "user_id": user_id,
            "count": len(recommendations),
            "recommendations": recommendations
        }

    except HTTPException:
        # Re-raise explicit HTTPExceptions (like 404) without converting to 500
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating recommendations: {str(e)}"
        )