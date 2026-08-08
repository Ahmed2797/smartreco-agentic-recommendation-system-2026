import os
from typing import List, Dict, Any, TypedDict
from langgraph.graph import StateGraph, END
from langsmith import traceable

# Custom Internal Imports
from src.chatmodel.llm import test_openai_api
from src.embeddings.embedding import get_text_embedding
from src.embeddings.vector_store import search_similar_products
from src.prompt.recommendation_prompt import (
    get_behavior_analysis_prompt,
    get_persuasive_recommendation_prompt
)

# Ensure LangSmith Tracing Environment Variables are active
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "true")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGCHAIN_ENDPOINT", "https://api.smith.langchain.com")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "smartreco-build-challenge-2026")


# 1. FIXED: State Schema includes search_query & refined_products metadata
class RecommendationAgentState(TypedDict):
    user_id: int
    search_query: str  # <--- Added active search context
    user_events: List[Dict[str, Any]]
    user_summary: str
    retrieved_matches: List[Dict[str, Any]]
    refined_products: List[Dict[str, Any]]  # <--- Stores full dicts, not just IDs
    filtered_product_ids: List[int]
    narrative: str
    needs_refinement: bool


# ==========================================
# Traced Reasoning Nodes
# ==========================================

@traceable(name="Analyze User Behavior Node")
def analyze_behavior_node(state: RecommendationAgentState) -> Dict[str, Any]:
    events = state.get("user_events", [])
    search_query = state.get("search_query", "").strip()

    # Priority 1: Give highest weight to explicit search queries
    if search_query:
        summary = f"User is actively searching for '{search_query}'."
        if events:
            summary += f" Recent historical context: {events[-3:]}"
        return {"user_summary": summary}

    if not events:
        return {"user_summary": "General interest in popular, high-rated items."}

    # Summarize recent events
    summarized_actions = [
        f"Event: {e.get('event_type')}, Details: {e.get('description') or e.get('event_data')}"
        for e in events[-10:]
    ]
    actions_str = "; ".join(summarized_actions)

    prompt = get_behavior_analysis_prompt(actions_str)
    response = test_openai_api(prompt)
    # print(f"get_behavior_analysis_prompt{response}")

    return {"user_summary": response}


@traceable(name="Retrieve Products Vector Search Node")
def retrieve_products_node(state: RecommendationAgentState) -> Dict[str, Any]:
    # Priority: Use search query directly if available, otherwise use LLM user summary
    search_query = state.get("search_query", "").strip()
    summary = search_query if search_query else state.get("user_summary", "top rated products")
    
    # 1. Vector Search using text embeddings
    query_vector = get_text_embedding(summary)
    matches = search_similar_products(query_vector=query_vector, top_k=3)
    
    return {"retrieved_matches": matches or []}


@traceable(name="Evaluate and Refine Node")
def evaluate_and_refine_node(state: RecommendationAgentState) -> Dict[str, Any]:
    matches = state.get("retrieved_matches", [])
    
    # 1. Filter products with score threshold
    refined_matches = [m for m in matches if m.get("score", 0.0) >= 0.8]
    
    # 2. FALLBACK: If similarity threshold was too strict, grab the top 3 matches anyway
    if not refined_matches and matches:
        refined_matches = matches[:5]

    # 3. Ensure product IDs are converted cleanly to standard integers
    refined_ids = []
    for m in refined_matches:
        try:
            p_id = int(m.get("id") or m.get("product_id"))
            refined_ids.append(p_id)
        except (ValueError, TypeError):
            continue

    return {
        "refined_products": refined_matches,
        "filtered_product_ids": refined_ids
    }


@traceable(name="Generate Persuasive Narrative Node")
def generate_persuasive_narrative_node(state: RecommendationAgentState) -> Dict[str, Any]:
    summary = state.get("user_summary", "")
    search_query = state.get("search_query", "")
    refined_products = state.get("refined_products", [])
    
    # Extract titles instead of sending raw IDs to the LLM
    product_titles = [
        p.get("title") or p.get("name") or f"Product #{p.get('id')}" 
        for p in refined_products
    ]
    

    prompt = get_persuasive_recommendation_prompt(
        user_summary=search_query if search_query else summary,
        product_titles=product_titles
    )
    response = test_openai_api(prompt)

    return {"narrative": response}


# ==========================================
# LangGraph Workflow Definition
# ==========================================

def build_langgraph_agent():
    workflow = StateGraph(RecommendationAgentState)

    workflow.add_node("analyze_behavior", analyze_behavior_node)
    workflow.add_node("retrieve_products", retrieve_products_node)
    workflow.add_node("evaluate_and_refine", evaluate_and_refine_node)
    workflow.add_node("generate_persuasive_narrative", generate_persuasive_narrative_node)

    workflow.set_entry_point("analyze_behavior")
    workflow.add_edge("analyze_behavior", "retrieve_products")
    workflow.add_edge("retrieve_products", "evaluate_and_refine")
    workflow.add_edge("evaluate_and_refine", "generate_persuasive_narrative")
    workflow.add_edge("generate_persuasive_narrative", END)

    return workflow.compile()


langgraph_recommendation_app = build_langgraph_agent()


# ==========================================
# Execution Handler
# ==========================================

@traceable(name="SmartReco LangGraph Agent Execution", run_type="chain")
def run_agentic_recommendation(
    user_id: int, 
    user_events: List[Dict[str, Any]], 
    search_query: str = ""
) -> Dict[str, Any]:
    
    initial_state: RecommendationAgentState = {
        "user_id": user_id,
        "search_query": search_query,  # <--- Pass active search string here
        "user_events": user_events,
        "user_summary": "",
        "retrieved_matches": [],
        "refined_products": [],
        "filtered_product_ids": [],
        "narrative": "",
        "needs_refinement": False
    }

    final_state = langgraph_recommendation_app.invoke(
        initial_state,
        config={"run_name": f"User_{user_id}_Recommendation_Run"}
    )

    return {
        "narrative": final_state.get("narrative", ""),
        "recommended_product_ids": final_state.get("filtered_product_ids", []),
        "user_summary": final_state.get("user_summary", "")
    }