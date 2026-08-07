from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel

from src.database.db import get_db
from src.database import models
from src.routes.auth import get_current_user
from src.services.engine import generate_real_recommendations

router = APIRouter(
    prefix="/api/recommendations",
    tags=["Recommendations"]
)


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
        from_attributes = True  # Supports direct SQLAlchemy model serialization


class RecommendationResponse(BaseModel):
    user_id: int
    count: int
    recommendations: List[RecommendationItem]


# =====================================
# Recommendation Endpoints
# =====================================

@router.get(
    "/me",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK
)
def get_my_recommendations(
    top_k: int = 5,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Fetches real-time recommendations tailored to the currently logged-in user.
    """
    try:
        recommended_products = generate_real_recommendations(
            user_id=current_user.id,
            db=db,
            top_k=top_k
        )

        return {
            "user_id": current_user.id,
            "count": len(recommended_products),
            "recommendations": recommended_products
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching recommendations: {str(e)}"
        )


@router.get(
    "/{user_id}",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK
)
def get_recommendations_by_user_id(
    user_id: int,
    top_k: int = 5,
    db: Session = Depends(get_db)
):
    """
    Get personalized product recommendations for a specific user ID (Admin/Testing).
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found."
        )

    try:
        recommended_products = generate_real_recommendations(
            user_id=user_id,
            db=db,
            top_k=top_k
        )

        return {
            "user_id": user_id,
            "count": len(recommended_products),
            "recommendations": recommended_products
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating recommendations: {str(e)}"
        )