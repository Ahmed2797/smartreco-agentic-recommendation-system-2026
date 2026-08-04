from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import search_similar_products

def retrieve_relevant_products_pipeline(user_intent_summary: str, top_k: int = 3) -> list:
    """Retrieve relevant products based on user intent summary."""
    query_vector = get_text_embedding(user_intent_summary)
    matches = search_similar_products(query_vector=query_vector, top_k=top_k)
    
    # Cosine score thresholding: Filter matches with a score of 0.5 or higher
    matched_ids = [int(m["id"]) for m in matches if m.get("score", 0.0) >= 0.5]
    if not matched_ids and matches:
        matched_ids = [int(m["id"]) for m in matches[:3]]
        
    return matched_ids