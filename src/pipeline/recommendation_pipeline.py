import sys
import os
from typing import Optional
from sqlalchemy.orm import Session

from src.database import models, crud
from src.pipeline.retrieval_pipeline import retrieve_relevant_products_pipeline
from src.prompt.recommendation_prompt import get_persuasive_recommendation_prompt
from src.chatmodel.mesh_client import mesh_client
from src.chatmodel.llm import test_openai_api


def execute_recommendation_pipeline(user_id: int, db: Session) -> Optional[models.Recommendation]:
    """
    Executes the complete RAG Recommendation Pipeline:
    1. Fetches recent user events.
    2. Runs vector semantic retrieval for relevant products.
    3. Generates LLM persuasive narrative.
    4. Saves and returns the Recommendation record.
    """
    # 1. Fetch recent activity events directly from DB (Optimized query limit)
    events = (
        db.query(models.ActivityEvent)
        .filter(models.ActivityEvent.user_id == user_id)
        .order_by(models.ActivityEvent.created_at.desc())
        .limit(8)
        .all()
    )

    if not events:
        print(f"⚠️ No activity events found for User {user_id}.")
        return None

    # Reverse events to keep chronological order (Oldest to Newest of the last 8)
    events.reverse()
    actions_summary = "; ".join([f"{e.event_type}: {e.event_data}" for e in events])

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

    # 4. LLM Execution via Mesh API (With Exception Handling)
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

        # narrative = test_openai_api(prompt)

    except Exception as e:
        print(f"❌ Mesh LLM API Error: {e}")
        # Fallback narrative in case LLM fails
        narrative = f"Based on your interest in {actions_summary[:50]}..., we highly recommend these top courses."

    # 5. Save result in Recommendation DB using CRUD / Session
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