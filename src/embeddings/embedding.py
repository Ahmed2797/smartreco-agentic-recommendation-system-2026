import os
from openai import OpenAI

from src.utils.logger import get_logger

logger = get_logger(__name__)
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required to generate embeddings")
        _client = OpenAI(api_key=api_key)
    return _client

def get_text_embedding(text: str) -> list:
    """
    Generates text embedding using official OpenAI API (text-embedding-3-small)
    """
    try:
        if not text or not text.strip():
            raise ValueError("Embedding input cannot be empty")
        response = _get_client().embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception:
        logger.exception("Embedding generation failed")
        raise
