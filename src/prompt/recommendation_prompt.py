def get_behavior_analysis_prompt(actions_summary: str) -> str:
    return f"""
    Analyze the following user behavior log:
    ---
    {actions_summary}
    ---
    Provide a 3-5 sentence summary of the user's explicit intent and current topics of focus.
    """

def get_persuasive_recommendation_prompt(user_summary: str, product_titles: list) -> str:
    titles_str = ", ".join(product_titles)
    return f"""
    User Intent Summary: "{user_summary}"
    Selected Relevant Courses: {titles_str}

    Write a short (3-5 sentences), persuasive narrative to show on the user's home feed. Explain directly to the user why these specific courses align with their recent actions and why taking action now matters for their career.
    
    # CRITICAL CONSTRAINTS:
        # - NEVER mention product ID numbers (e.g., do NOT say "product IDs 76, 78").
        # - Highlight the product titles or themes directly.
        # - Keep it under 100 words.
    """