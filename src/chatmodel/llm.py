
from openai import OpenAI
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required for LLM recommendations")
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client

def test_openai_api(prompt: str) -> str:
    """
    Test the OpenAI API integration by sending a simple chat completion request.
    Ensure that the OPENAI_API_KEY is set in the environment variables.
    """
    if not prompt.strip():
        raise ValueError("LLM prompt cannot be empty")
    logger.info("Requesting recommendation narrative from OpenAI")
    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",  # Fast and cost-effective model
        messages=[
            {"role": "system", "content": "You are a helpful AI recommendation assistant."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
    )

    content = response.choices[0].message.content
    if not content:
        raise RuntimeError("OpenAI returned an empty recommendation narrative")
    logger.info("OpenAI recommendation narrative received")
    return content.strip()
