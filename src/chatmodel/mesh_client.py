from meshapi import MeshAPI
from meshapi import MeshAPI, ChatCompletionParams, ChatMessage
from src.config.settings import settings

if not settings.MESH_API_KEY:
        raise ValueError("MESH_API_KEY is not set in environment variables.")

mesh_client = MeshAPI(base_url="https://api.meshapi.ai", token=settings.MESH_API_KEY)


def test_mesh_api(prompt: str):
    """
    Test the Mesh API integration by sending a simple chat completion request.
    Ensure that the MESH_API_KEY is set in the environment variables.
    """
    
    reply = mesh_client.chat.completions.create(
        ChatCompletionParams(
            model="openai/gpt-4o-mini",
            messages=[
                ChatMessage(role="user", content=prompt),
            ],
            temperature=0.7,
            max_tokens=256,
        )
    )
    
    print("Mesh API Test Reply:", reply.choices[0].message.content)

    return reply.choices[0].message.content.strip()

