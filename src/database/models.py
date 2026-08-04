from sqlalchemy import Column, Integer, String, Float, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from src.database.db import Base


# =====================================
# 1. User Model
# =====================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    activities = relationship("UserActivity", back_populates="user", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    events = relationship("UserEvent", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


# =====================================
# 2. Product Model
# =====================================
class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)
    price = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    recommendations = relationship("Recommendation", back_populates="product")
    def __repr__(self):
        return f"<Product(id={self.id}, title='{self.title}')>"


# =====================================
# 3. User Activity / Behavioral Event Model
# =====================================
class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)  # e.g., 'view_page', 'product_click', 'search_query', 'add_to_cart', 'time_spent'
    event_data = Column(Text, nullable=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User", back_populates="activities")
    def __repr__(self):
        return f"<UserActivity(id={self.id}, user_id={self.user_id}, event_type='{self.event_type}')>"


class UserEvent(Base):
    __tablename__ = "user_events"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_type = Column(String(50), nullable=False)  # search, page_view, add_to_cart
    description = Column(Text, nullable=True)
    product_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="events")

# =====================================
# 4. Recommendation Output Model
# =====================================
class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)  # Similarity or confidence score (e.g., 0.95)
    algorithm_used = Column(String(50), default="hybrid_v1")  # Model identification
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="recommendations")
    product = relationship("Product", back_populates="recommendations")

    def __repr__(self):
        return f"<Recommendation(user_id={self.user_id}, product_id={self.product_id}, score={self.score})>"


# =====================================
# Database Performance Indexes
# =====================================
# Compound index for fast timeline queries per user
Index("ix_user_activity_user_time", UserActivity.user_id, UserActivity.created_at.desc())