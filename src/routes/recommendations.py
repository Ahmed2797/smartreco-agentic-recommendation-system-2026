from typing import List, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.database.db import get_db
from src.database import models
from src.routes.auth import get_current_user

from src.pipeline.retrieval_pipeline import (
    retrieve_relevant_products_pipeline
)

from src.prompt.recommendation_prompt import (
    get_persuasive_recommendation_prompt
)

# from src.chatmodel.mesh_client import mesh_client
from src.chatmodel.llm import _get_client

from src.utils.logger import get_logger


# ============================================================
# Logger
# ============================================================

logger = get_logger(__name__)


# ============================================================
# RAG + Mesh API Execution Pipeline
# ============================================================

def execute_recommendation_pipeline(
    user_id: int,
    db: Session
) -> Optional[models.Recommendation]:

    """
    Complete recommendation pipeline:

    1. Fetch recent user activities
    2. Create activity summary
    3. Perform semantic/vector retrieval
    4. Fetch matching products from database
    5. Generate recommendation prompt
    6. Generate narrative using Mesh/OpenAI
    7. Save recommendation in database
    """

    logger.info(
        "============================================================"
    )

    logger.info(
        f"STARTING RECOMMENDATION PIPELINE | USER={user_id}"
    )

    logger.info(
        "============================================================"
    )

    # ========================================================
    # 1. Find Activity Model
    # ========================================================

    ActivityModel = getattr(
        models,
        "UserActivity",
        getattr(models, "ActivityEvent", None)
    )

    if not ActivityModel:

        logger.error(
            "Neither UserActivity nor ActivityEvent model found."
        )

        return None

    # ========================================================
    # 2. Fetch Recent User Activities
    # ========================================================

    try:

        events = (
            db.query(ActivityModel)
            .filter(ActivityModel.user_id == user_id)
            .order_by(ActivityModel.created_at.desc())
            .limit(8)
            .all()
        )

        logger.info(
            f"USER={user_id} | EVENTS LOADED={len(events)}"
        )

    except Exception as e:

        logger.exception(
            f"Failed to load user activities | USER={user_id}"
        )

        return None

    # ========================================================
    # 3. No Activity -> Cold Start
    # ========================================================

    if not events:

        logger.warning(
            f"USER={user_id} | NO ACTIVITY EVENTS FOUND"
        )

        return None

    # ========================================================
    # 4. Reverse Events
    # Newest -> Oldest
    # becomes
    # Oldest -> Newest
    # ========================================================

    events.reverse()

    # ========================================================
    # 5. Create Activity Summary
    # ========================================================

    actions_summary = "; ".join(
        [
            (
                f"{e.event_type}: "
                f"{getattr(e, 'event_data', '') or getattr(e, 'description', '')}"
            )
            for e in events
        ]
    )

    logger.info(
        f"USER={user_id} | ACTION SUMMARY={actions_summary}"
    )

    # ========================================================
    # 6. RAG / Semantic Retrieval
    # ========================================================

    logger.info(
        f"USER={user_id} | STARTING RAG RETRIEVAL"
    )

    try:

        matched_ids = retrieve_relevant_products_pipeline(
            actions_summary
        )

    except Exception as e:

        logger.exception(
            f"RAG RETRIEVAL FAILED | USER={user_id}"
        )

        return None

    logger.info(
        f"USER={user_id} | RAG MATCHED PRODUCT IDS={matched_ids}"
    )

    # ========================================================
    # 7. RAG Returned Nothing
    # ========================================================

    if not matched_ids:

        logger.warning(
            f"USER={user_id} | RAG RETURNED NO PRODUCTS"
        )

        return None

    # ========================================================
    # 8. Fetch Products From Database
    # ========================================================

    try:

        products_db = (
            db.query(models.Product)
            .filter(
                models.Product.id.in_(matched_ids)
            )
            .all()
        )

    except Exception as e:

        logger.exception(
            f"DATABASE PRODUCT QUERY FAILED | USER={user_id}"
        )

        return None

    logger.info(
        f"USER={user_id} | PRODUCTS FOUND IN DB={len(products_db)}"
    )

    # ========================================================
    # 9. Create Product Map
    # ========================================================

    product_map = {
        product.id: product
        for product in products_db
    }

    # ========================================================
    # 10. Preserve RAG Ranking Order
    # ========================================================

    ordered_products = [
        product_map[product_id]
        for product_id in matched_ids
        if product_id in product_map
    ]

    product_titles = [
        product.title
        for product in ordered_products
    ]

    logger.info(
        f"USER={user_id} | PRODUCT TITLES={product_titles}"
    )

    # ========================================================
    # 11. Generate Recommendation Prompt
    # ========================================================

    try:

        prompt = get_persuasive_recommendation_prompt(
            actions_summary,
            product_titles
        )

        logger.info(
            f"USER={user_id} | RECOMMENDATION PROMPT GENERATED"
        )

        logger.debug(
            f"USER={user_id} | PROMPT={prompt}"
        )

    except Exception as e:

        logger.exception(
            f"PROMPT GENERATION FAILED | USER={user_id}"
        )

        return None

    # ========================================================
    # 12. Mesh / OpenAI LLM
    # ========================================================

    try:

        logger.info(
            f"USER={user_id} | CALLING MESH LLM"
        )

        response = _get_client().chat.completions.create(

            model="openai/gpt-4o-mini",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert AI "
                        "product recommender assistant."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.5
        )

        narrative = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        logger.info(
            f"USER={user_id} | MESH LLM COMPLETED"
        )

        logger.debug(
            f"USER={user_id} | NARRATIVE={narrative}"
        )

    except Exception as e:

        logger.exception(
            f"MESH LLM FAILED | USER={user_id}"
        )

        first_product = (
            product_titles[0]
            if product_titles
            else "our courses"
        )

        narrative = (
            f"Based on your recent interest in "
            f"{first_product}, we highly recommend "
            f"these selections."
        )

    # ========================================================
    # 13. Save Recommendation
    # ========================================================

    try:

        rec = models.Recommendation(

            user_id=user_id,

            narrative=narrative,

            # IMPORTANT:
            # Store ALL RAG matched product IDs
            recommended_product_ids=matched_ids
        )

        db.add(rec)

        db.commit()

        db.refresh(rec)

        logger.info(
            f"USER={user_id} | "
            f"RECOMMENDATION SAVED | ID={rec.id}"
        )

        logger.info(
            "============================================================"
        )

        logger.info(
            f"RECOMMENDATION PIPELINE COMPLETED | USER={user_id}"
        )

        logger.info(
            "============================================================"
        )

        return rec

    except Exception as e:

        db.rollback()

        logger.exception(
            f"FAILED TO SAVE RECOMMENDATION | USER={user_id}"
        )

        return None


# ============================================================
# Helper Function
# ============================================================

def _get_ordered_products_with_scores(
    product_ids: List[int],
    db: Session
) -> List[models.Product]:

    if not product_ids:

        return []

    # ========================================================
    # Fetch products
    # ========================================================

    products_db = (
        db.query(models.Product)
        .filter(
            models.Product.id.in_(product_ids)
        )
        .all()
    )

    # ========================================================
    # Product Map
    # ========================================================

    product_map = {
        product.id: product
        for product in products_db
    }

    ordered_products = []

    # ========================================================
    # Preserve RAG Ranking
    # ========================================================

    for index, product_id in enumerate(product_ids):

        if product_id not in product_map:

            logger.warning(
                f"Product ID={product_id} "
                f"was returned by RAG but not found in database."
            )

            continue

        product = product_map[product_id]

        # Display score based on ranking position
        calculated_score = max(
            70,
            98 - (index * 4)
        )

        # Only use this if Product model has a score column
        #
        # product.score = f"{calculated_score}%"

        ordered_products.append(product)

    return ordered_products


# ============================================================
# Response Schemas
# ============================================================

class RecommendationItem(BaseModel):

    id: int

    title: str

    description: Optional[str] = None

    category: str

    price: float

    score: Optional[str] = None

    class Config:
        from_attributes = True


class RecommendationResponse(BaseModel):

    user_id: int

    narrative: str

    count: int

    recommendations: List[RecommendationItem]


# ============================================================
# FastAPI Router
# ============================================================

router = APIRouter(

    prefix="/api/recommendations",

    tags=["Recommendations"]
)


# ============================================================
# GET CURRENT USER RECOMMENDATIONS
# ============================================================

@router.get(
    "/me",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK
)
def get_my_recommendations(

    db: Session = Depends(get_db),

    current_user: models.User = Depends(
        get_current_user
    )
):

    """
    Generate recommendations for the
    currently authenticated user.
    """

    logger.info(
        f"🔥 /api/recommendations/me CALLED | "
        f"USER={current_user.id}"
    )

    try:

        # ====================================================
        # Run recommendation pipeline
        # ====================================================

        rec_record = execute_recommendation_pipeline(

            user_id=current_user.id,

            db=db
        )

        logger.info(
            f"USER={current_user.id} | "
            f"PIPELINE RESULT={rec_record}"
        )

        # ====================================================
        # Cold Start / Fallback
        # ====================================================

        if (
            not rec_record
            or not rec_record.recommended_product_ids
        ):

            logger.warning(
                f"USER={current_user.id} | "
                f"USING COLD START FALLBACK"
            )

            fallback_products = (
                db.query(models.Product)
                .limit(5)
                .all()
            )

            return {

                "user_id": current_user.id,

                "narrative": (
                    "Welcome to SmartReco AI! "
                    "Here are our top featured courses "
                    "to start your learning journey."
                ),

                "count": len(fallback_products),

                "recommendations": fallback_products
            }

        # ====================================================
        # Get Ordered Products
        # ====================================================

        ordered_products = (
            _get_ordered_products_with_scores(

                rec_record.recommended_product_ids,

                db
            )
        )

        logger.info(
            f"USER={current_user.id} | "
            f"RETURNING {len(ordered_products)} PRODUCTS"
        )

        # ====================================================
        # API Response
        # ====================================================

        return {

            "user_id": current_user.id,

            # IMPORTANT:
            # Return the string narrative
            # NOT the Recommendation object

            "narrative": rec_record.narrative,

            "count": len(ordered_products),

            "recommendations": ordered_products
        }

    except Exception as e:

        logger.exception(
            f"RECOMMENDATION API FAILED | "
            f"USER={current_user.id}"
        )

        raise HTTPException(

            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "An error occurred while "
                "generating recommendations."
            )
        )


# ============================================================
# GET RECOMMENDATIONS BY USER ID
# ============================================================

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
    Generate recommendations for a specific user.

    Intended for admin / inspection usage.
    """

    logger.info(
        f"🔥 /api/recommendations/{user_id} CALLED"
    )

    # ========================================================
    # Check User
    # ========================================================

    user = (
        db.query(models.User)
        .filter(
            models.User.id == user_id
        )
        .first()
    )

    if not user:

        logger.warning(
            f"USER={user_id} NOT FOUND"
        )

        raise HTTPException(

            status_code=status.HTTP_404_NOT_FOUND,

            detail=(
                f"User with ID {user_id} not found."
            )
        )

    try:

        # ====================================================
        # Run recommendation pipeline
        # ====================================================

        rec_record = execute_recommendation_pipeline(

            user_id=user_id,

            db=db
        )

        # ====================================================
        # Cold Start / Fallback
        # ====================================================

        if (
            not rec_record
            or not rec_record.recommended_product_ids
        ):

            logger.warning(
                f"USER={user_id} | "
                f"USING FALLBACK PRODUCTS"
            )

            fallback_products = (
                db.query(models.Product)
                .limit(5)
                .all()
            )

            return {

                "user_id": user_id,

                "narrative": (
                    "No activity history found. "
                    "Displaying general course catalogue."
                ),

                "count": len(fallback_products),

                "recommendations": fallback_products
            }

        # ====================================================
        # Ordered Products
        # ====================================================

        ordered_products = (
            _get_ordered_products_with_scores(

                rec_record.recommended_product_ids,

                db
            )
        )

        logger.info(
            f"USER={user_id} | "
            f"RETURNING {len(ordered_products)} PRODUCTS"
        )

        # ====================================================
        # Final Response
        # ====================================================

        return {

            "user_id": user_id,

            "narrative": rec_record.narrative,

            "count": len(ordered_products),

            "recommendations": ordered_products
        }

    except Exception as e:

        logger.exception(
            f"RECOMMENDATION API FAILED | "
            f"USER={user_id}"
        )

        raise HTTPException(

            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),

            detail=(
                "An error occurred while "
                "fetching user recommendations."
            )
        )
