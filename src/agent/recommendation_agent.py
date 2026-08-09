from sqlalchemy.orm import Session, joinedload
from src.database import models
from src.chatmodel.llm import test_openai_api
from src.chatmodel.mesh_client import test_mesh_api

from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import search_similar_products
from src.agent.langgraph_agent import run_agentic_recommendation
from src.utils.logger import get_logger

logger = get_logger(__name__)


def generate_behavioral_recommendation(user_events: list, available_products: list = None):
    """
    User recent browsing behavior (user_events) and available products are used 
    to generate a personalized recommendation narrative via vector search.
    """
    activities_summary = ", ".join([
        f"Event: {e.get('event_type', '')}, Context: {e.get('description', '') or e.get('event_data', '')}" 
        for e in user_events[-10:]
    ]) if user_events else "Popular trending products"

    # 1. Semantic Search Vector Embedding & Search
    try:
        user_query_vector = get_text_embedding(activities_summary)
        matches = search_similar_products(user_query_vector, top_k=3)
    except Exception:
        logger.exception("Behavioral retrieval failed")
        return "We could not personalize recommendations right now.", []

    matched_ids = []
    for match in matches or []:
        try:
            matched_ids.append(int(match["id"]))
        except (KeyError, TypeError, ValueError):
            logger.warning("Ignoring vector result with invalid product id")

    # 2. Persuasive Narrative generation with LLM
    prompt = f"""
    You are an expert AI product recommendation advisor. 
    User's recent browsing behavior: {activities_summary}
    Relevant recommended product IDs: {matched_ids}
    
    Write a short, engaging, and highly persuasive recommendation narrative (2-3 sentences) 
    explaining WHY these specific products match their recent intent.
    """
    
    try:
        response = test_openai_api(prompt)
    except Exception:
        logger.exception("Behavioral narrative generation failed")
        response = "Here are products selected from your recent activity."
    return response, matched_ids



def generate_and_save_user_recommendation(user_id: int, db: Session):
    """
    Fetches user activity, performs vector similarity search on Pinecone,
    generates an AI narrative, and saves products + scores to SQL DB.
    """
    # 1. Fetch user activity events
    events = (
        db.query(models.UserActivity)
        .options(joinedload(models.UserActivity.product))
        .filter(models.UserActivity.user_id == user_id)
        .order_by(models.UserActivity.created_at.desc())
        .limit(10)
        .all()
    )

    # 2. Build behavior text summary for vector search
    activities_summary = ", ".join([
        f"{e.event_type}: {e.event_data or (e.product.title if e.product else '')}"
        for e in events
    ]) if events else "popular tech gadgets"

    # 3. Vector Search on Pinecone
    try:
        user_query_vector = get_text_embedding(activities_summary)
        matches = search_similar_products(user_query_vector, top_k=3)
        logger.exception("Recommendation retrieval for user_id=%s", user_id)

    except Exception:
        logger.exception("Recommendation retrieval failed for user_id=%s", user_id)
        matches = []

    # 4. Clear previous recommendations for this user
    saved_ids = []
    try:
        db.query(models.Recommendation).filter(models.Recommendation.user_id == user_id).delete()
        for match in matches:
            try:
                prod_id = int(match["id"])
                vector_score = round(float(match.get("score", 0)), 2)
            except (KeyError, TypeError, ValueError):
                logger.warning("Ignoring invalid vector match for user_id=%s", user_id)
                continue
            db.add(models.Recommendation(
                user_id=user_id, product_id=prod_id, score=vector_score,
                algorithm_used="pinecone_vector_v1",
            ))
            saved_ids.append(prod_id)
        db.commit()
        logger.info("Saved %s recommendations for user_id=%s", len(saved_ids), user_id)
    except Exception:
        db.rollback()
        logger.exception("Failed to save recommendations for user_id=%s", user_id)

    # 6. Generate narrative via LLM using matched IDs
    prompt = f"""
    You are an AI e-commerce assistant.
    User interest summary: {activities_summary}
    Recommended product IDs: {saved_ids}
    
    Write a 2-sentence persuasive reason why these products fit their intent.
    """
    try:
        narrative = test_openai_api(prompt)
    except Exception:
        logger.exception("Mesh narrative generation failed for user_id=%s", user_id)
        narrative = "Here are products selected from your recent activity."

    return {
        "user_id": user_id,
        "narrative": narrative,
        "recommended_product_ids": saved_ids
    }
