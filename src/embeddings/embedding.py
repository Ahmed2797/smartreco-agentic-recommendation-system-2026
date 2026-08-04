from meshapi import EmbeddingsParams
from src.chatmodel.mesh_client import mesh_client

def get_text_embedding(text: str) -> list:
    """Mesh API use text-embedding-3-small model to generate embeddings for the given text."""
    response = mesh_client.embeddings.create(
        EmbeddingsParams(
            model="openai/text-embedding-ada-002",
            input=text
        )
    )
    return response.data[0].embedding

import os
from openai import OpenAI

# Initialize standard OpenAI client using official API Key
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

def get_text_embedding(text: str) -> list:
    """
    Generates text embedding using official OpenAI API (text-embedding-3-small)
    """
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"❌ OpenAI Embedding Error: {str(e)}")
        raise e