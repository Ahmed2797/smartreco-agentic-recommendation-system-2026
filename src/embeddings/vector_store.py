from pinecone import Pinecone, ServerlessSpec
from src.config.settings import settings

pc = Pinecone(api_key=settings.PINECONE_API_KEY)

# Pinecone Index Creation: Check if the index exists, if not create it
if settings.PINECONE_INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
    pc.create_index(
        name=settings.PINECONE_INDEX_NAME,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(settings.PINECONE_INDEX_NAME)

def upsert_product_to_vector_db(product_id: int, vector: list, metadata: dict):
    """Dual-Write Engine: SQL-Pinecone-Sync."""
    index.upsert(
        vectors=[{
            "id": str(product_id),
            "values": vector,
            "metadata": metadata
        }]
    )

def search_similar_products(query_vector: list, top_k: int = 3):
    response = index.query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )
    return response.get("matches", [])