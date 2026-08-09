from pinecone import Pinecone, ServerlessSpec
from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
_index = None


def _get_index():
    """Create the remote client only when vector search is actually requested."""
    global _index
    if _index is not None:
        return _index
    if not settings.PINECONE_API_KEY:
        raise RuntimeError("PINECONE_API_KEY is required for vector search")

    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index_names = [item.name for item in pc.list_indexes()]
    if settings.PINECONE_INDEX_NAME not in index_names:
        logger.info("Creating Pinecone index '%s'", settings.PINECONE_INDEX_NAME)
        pc.create_index(
            name=settings.PINECONE_INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    _index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _index

def upsert_product_to_vector_db(product_id: int, vector: list, metadata: dict):
    """Dual-Write Engine: SQL-Pinecone-Sync."""
    _get_index().upsert(
        vectors=[{
            "id": str(product_id),
            "values": vector,
            "metadata": metadata
        }]
    )

def search_similar_products(query_vector: list, top_k: int = 3):
    if not query_vector:
        raise ValueError("Query vector cannot be empty")
    response = _get_index().query(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True
    )
    return response.get("matches", [])
