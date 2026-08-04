# src/database/crud.py

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database import models


# =====================================
# User Operations
# =====================================

def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, email: str, password: str, role: str = "user") -> models.User:
    user = models.User(email=email, password=password, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
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
    narrative: str,
    recommended_product_ids: list
) -> models.Recommendation:
    recommendation = models.Recommendation(
        user_id=user_id,
        narrative=narrative,
        recommended_product_ids=recommended_product_ids
    )
    db.add(recommendation)
    db.commit()
    db.refresh(recommendation)
    return recommendation


def get_latest_recommendation(db: Session, user_id: int) -> Optional[models.Recommendation]:
    return (
        db.query(models.Recommendation)
        .filter(models.Recommendation.user_id == user_id)
        .order_by(models.Recommendation.created_at.desc())
        .first()
    )