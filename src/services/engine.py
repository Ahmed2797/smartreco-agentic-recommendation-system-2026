from sqlalchemy.orm import Session
from src.database import models
from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import search_similar_products

def get_user_events_from_db(user_id: int, db: Session, limit: int = 10) -> list[dict]:
    """Fetches real-time activity history for an authenticated user."""
    activities = (
        db.query(models.UserActivity)
        .filter(models.UserActivity.user_id == user_id)
        .order_by(models.UserActivity.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "user_id": act.user_id,
            "event_type": act.event_type,
            "event_data": act.event_data,
            "product_id": act.product_id
        }
        for act in activities
    ]

def generate_real_recommendations(user_id: int, db: Session, top_k: int = 5):
    # 1. Pull real events from SQLite/PostgreSQL
    user_events = get_user_events_from_db(user_id, db, limit=10)

    # 2. Cold Start Fallback: If user has no activity yet, return default/top products
    if not user_events:
        return db.query(models.Product).limit(top_k).all()

    # 3. Aggregate real user intent from searches and product clicks
    search_terms = [
        e["event_data"] for e in user_events if e["event_type"] == "search_query"
    ]
    product_clicks = [
        e["event_data"] for e in user_events if e["event_type"] == "product_click"
    ]
    
    context_text = " ".join(search_terms + product_clicks)
    if not context_text.strip():
        return db.query(models.Product).limit(top_k).all()

    # 4. Generate query vector from real user context
    query_vector = get_text_embedding(context_text)

    # 5. Perform real vector search
    recommended_ids = search_similar_products(query_vector, top_k=top_k)

    # 6. Query corresponding product records from SQL DB
    if not recommended_ids:
        return db.query(models.Product).limit(top_k).all()

    return (
        db.query(models.Product)
        .filter(models.Product.id.in_(recommended_ids))
        .all()
    )