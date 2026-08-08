from typing import List, Dict, Any, Union
from sqlalchemy.orm import Session
from src.database import models
from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import search_similar_products


class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_recommendations(self, user_id: int, limit: int = 4) -> List[models.Product]:
        """
        1. Pulls user activity from DB.
        2. Performs Pinecone vector similarity search.
        3. Persists recommendations & scores to SQL DB.
        4. Attaches formatted score strings (e.g., '94%') to products in original vector relevance order.
        """
        # 1. Fetch recent user activity
        activities = (
            self.db.query(models.UserActivity)
            .filter(models.UserActivity.user_id == user_id)
            .order_by(models.UserActivity.created_at.desc())
            .limit(10)
            .all()
        )

        # Build context from searches, clicks, and general interactions
        context_items = [
            f"{a.event_type}: {a.event_data}" for a in activities if a.event_data
        ]
        context_text = " ".join(context_items) if context_items else "AI Machine Learning"

        # 2. Pinecone Vector Search
        query_vector = get_text_embedding(context_text)
        raw_matches = search_similar_products(query_vector, top_k=limit)

        if not raw_matches:
            return self._get_fallback_products(limit)

        # Handle matches whether returned as dicts [{'id': '1', 'score': 0.94}] or plain IDs ['1', '2']
        score_map: Dict[int, float] = {}
        ordered_ids: List[int] = []

        for item in raw_matches:
            if isinstance(item, dict):
                p_id = int(item.get("id"))
                score = float(item.get("score", 0.85))
            else:
                p_id = int(item)
                score = 0.85

            if p_id not in score_map:
                score_map[p_id] = round(score, 2)
                ordered_ids.append(p_id)

        # 3. Fetch Product ORM objects from DB
        products_db = (
            self.db.query(models.Product)
            .filter(models.Product.id.in_(ordered_ids))
            .all()
        )

        if not products_db:
            return self._get_fallback_products(limit)

        # Preserve exact vector ranking order
        product_dict = {p.id: p for p in products_db}
        ordered_products = [product_dict[p_id] for p_id in ordered_ids if p_id in product_dict]

        # 4. Save to Database Recommendation table
        self._save_recommendations_to_db(user_id, score_map)

        # 5. Attach formatted score string for dashboard HTML badges
        for prod in ordered_products:
            raw_score = score_map.get(prod.id, 0.85)
            prod.score = f"{int(raw_score * 100)}%"

        return ordered_products

    def _get_fallback_products(self, limit: int) -> List[models.Product]:
        products = self.db.query(models.Product).limit(limit).all()
        for p in products:
            p.score = "85%"
        return products

    def _save_recommendations_to_db(self, user_id: int, score_map: Dict[int, float]):
        try:
            self.db.query(models.Recommendation).filter(models.Recommendation.user_id == user_id).delete()
            for prod_id, score in score_map.items():
                rec_entry = models.Recommendation(
                    user_id=user_id,
                    product_id=prod_id,
                    score=score,
                    algorithm_used="pinecone_vector_v1"
                )
                self.db.add(rec_entry)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Failed to save recommendations: {str(e)}")


def generate_real_recommendations(user_id: int, db: Session, top_k: int = 5) -> List[models.Product]:
    """
    Wrapper function maintaining backwards compatibility for existing route imports.
    """
    engine = RecommendationEngine(db)
    return engine.generate_recommendations(user_id=user_id, limit=top_k)