from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from collections import defaultdict

from src.database import models


# Event Types Weighted Score Config
EVENT_WEIGHTS = {
    "view_page": 1,
    "product_click": 2,
    "search_query": 3,
    "add_to_cart": 5,
    "time_spent": 2
}


class RecommendationEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_recommendations(self, user_id: int, limit: int = 6) -> List[models.Product]:
        """
        Generates personalized product recommendations for a user based on 
        their interaction history, category preference, and behavioral weight.
        """
        # 1. Fetch User Activity Logs
        activities = (
            self.db.query(models.UserActivity)
            .filter(models.UserActivity.user_id == user_id)
            .order_by(models.UserActivity.created_at.desc())
            .limit(50)
            .all()
        )

        # Fallback: If no activity exists for this user, return top/popular products
        if not activities:
            return self._get_fallback_popular_products(limit)

        # 2. Calculate Category Scores & Interacted Product IDs
        category_scores = defaultdict(float)
        interacted_product_ids = set()

        for act in activities:
            weight = EVENT_WEIGHTS.get(act.event_type, 1)

            # If activity is directly tied to a product
            if act.product_id:
                interacted_product_ids.add(act.product_id)
                product = self.db.query(models.Product).filter(models.Product.id == act.product_id).first()
                if product:
                    category_scores[product.category] += weight * 1.5

            # If activity is a search query
            if act.event_type == "search_query" and act.event_data:
                search_term = act.event_data.lower()
                matching_products = (
                    self.db.query(models.Product)
                    .filter(
                        models.Product.title.ilike(f"%{search_term}%") | 
                        models.Product.category.ilike(f"%{search_term}%")
                    )
                    .all()
                )
                for p in matching_products:
                    category_scores[p.category] += weight

        # If no categories matched, fallback to popular products
        if not category_scores:
            return self._get_fallback_popular_products(limit)

        # 3. Get Top Preferred Categories
        sorted_categories = sorted(category_scores.items(), key=lambda x: x[1], reverse=True)
        top_categories = [cat[0] for cat in sorted_categories[:3]]

        # 4. Fetch Recommended Products matching top categories (Excluding already interacted products)
        recommended_products = (
            self.db.query(models.Product)
            .filter(models.Product.category.in_(top_categories))
            .filter(models.Product.id.not_in(interacted_product_ids))
            .order_by(func.random())
            .limit(limit)
            .all()
        )

        # If not enough products found excluding interacted ones, allow all category products
        if len(recommended_products) < limit:
            additional_products = (
                self.db.query(models.Product)
                .filter(models.Product.category.in_(top_categories))
                .order_by(func.random())
                .limit(limit - len(recommended_products))
                .all()
            )
            # Remove duplicate objects
            seen_ids = {p.id for p in recommended_products}
            for p in additional_products:
                if p.id not in seen_ids:
                    recommended_products.append(p)

        # 5. Save generated recommendations into the DB Recommendation table
        self._save_recommendations_to_db(user_id, recommended_products, sorted_categories[0][1])

        return recommended_products

    def _get_fallback_popular_products(self, limit: int) -> List[models.Product]:
        """Returns top products when user history is empty (Cold Start problem)."""
        return self.db.query(models.Product).order_by(models.Product.id.desc()).limit(limit).all()

    def _save_recommendations_to_db(self, user_id: int, products: List[models.Product], max_score: float):
        """Persists generated recommendations to database."""
        try:
            # Clear old recommendations for user
            self.db.query(models.Recommendation).filter(models.Recommendation.user_id == user_id).delete()

            # Insert new recommendation entries
            for rank, product in enumerate(products, start=1):
                rec_score = round(max(0.1, (max_score / (rank * 2))), 2)
                rec_entry = models.Recommendation(
                    user_id=user_id,
                    product_id=product.id,
                    score=rec_score,
                    algorithm_used="behavioral_weight_v1"
                )
                self.db.add(rec_entry)

            self.db.commit()
        except Exception as e:
            self.db.rollback()
            print(f"Failed to save recommendations: {str(e)}")