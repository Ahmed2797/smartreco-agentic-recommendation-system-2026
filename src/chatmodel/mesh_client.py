from meshapi import MeshAPI, ChatCompletionParams, ChatMessage
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
mesh_client = (
    MeshAPI(base_url="https://api.meshapi.ai", token=settings.MESH_API_KEY)
    if settings.MESH_API_KEY else None
)


def get_mesh_client() -> MeshAPI:
    if mesh_client is None:
        raise RuntimeError("MESH_API_KEY is required for Mesh recommendations")
    return mesh_client


def test_mesh_api(prompt: str):
    """
    Test the Mesh API integration by sending a simple chat completion request.
    Ensure that the MESH_API_KEY is set in the environment variables.
    """
    
    logger.info("Requesting recommendation narrative from Mesh")
    reply = get_mesh_client().chat.completions.create(
        ChatCompletionParams(
            model="openai/gpt-4o-mini",
            messages=[
                ChatMessage(role="user", content=prompt),
            ],
            temperature=0.7,
            max_tokens=256,
        )
    )
    
    content = reply.choices[0].message.content
    if not content:
        raise RuntimeError("Mesh returned an empty recommendation narrative")
    logger.info("Mesh recommendation narrative received")
    return content.strip()
