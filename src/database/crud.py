# src/database/crud.py

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database import models
from src.utils.logger import get_logger

logger = get_logger(__name__)


# =====================================
# User Operations
# =====================================

def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, email: str, hashed_password: str, username: Optional[str] = None) -> models.User:
    """Create a user using the fields defined by the User model."""
    user = models.User(
        email=email,
        username=username or email.split("@", 1)[0],
        hashed_password=hashed_password,
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception("Failed to create user")
        raise
    logger.info("Created user_id=%s", user.id)
    return user


# =====================================
# Product Operations
# =====================================

def get_product_by_id(db: Session, product_id: int) -> Optional[models.Product]:
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def get_all_products(db: Session) -> List[models.Product]:
    return db.query(models.Product).all()


def get_products_by_category(db: Session, category: str) -> List[models.Product]:
    return db.query(models.Product).filter(models.Product.category == category).all()


# =====================================
# Activity Events
# =====================================

def save_activity_event(
    db: Session,
    user_id: int,
    event_type: str,
    event_data: str,
    product_id: Optional[int] = None
) -> models.UserActivity:
    event = models.UserActivity(
        user_id=user_id,
        product_id=product_id,
        event_type=event_type,
        event_data=event_data
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_user_events(db: Session, user_id: int, limit: int = 20) -> List[models.UserActivity]:
    return (
        db.query(models.UserActivity)
        .filter(models.UserActivity.user_id == user_id)
        .order_by(models.UserActivity.created_at.desc())
        .limit(limit)
        .all()
    )


# =====================================
# Recommendation History
# =====================================

def save_recommendation(
    db: Session,
    user_id: int,
    product_id: int,
    score: float,
    algorithm_used: str = "hybrid_v1",
) -> models.Recommendation:
    """Persist one product recommendation (the database stores one row per product)."""
    recommendation = models.Recommendation(
        user_id=user_id, product_id=product_id, score=score,
        algorithm_used=algorithm_used,
    )
    try:
        db.add(recommendation)
        db.commit()
        db.refresh(recommendation)
    except Exception:
        db.rollback()
        logger.exception("Failed to save recommendation for user_id=%s", user_id)
        raise
    return recommendation


def get_latest_recommendation(db: Session, user_id: int) -> Optional[models.Recommendation]:
    return (
        db.query(models.Recommendation)
        .filter(models.Recommendation.user_id == user_id)
        .order_by(models.Recommendation.created_at.desc())
        .first()
    )
