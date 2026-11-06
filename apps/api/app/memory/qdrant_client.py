import uuid
from typing import List, Optional
from qdrant_client import AsyncQdrantClient, models as qdrant_models
from app.core.config import settings

# Collection vector dimensions for fastembed's all-MiniLM-L6-v2 model
VECTOR_SIZE = 384
DISTANCE = qdrant_models.Distance.COSINE


def _collection_name(workspace_id: str) -> str:
    """Generate deterministic per-workspace Qdrant collection name for tenant isolation."""
    return f"workspace_{workspace_id}"


async def get_qdrant_client() -> AsyncQdrantClient:
    """Return an async Qdrant client from settings."""
    if settings.QDRANT_API_KEY:
        return AsyncQdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
    return AsyncQdrantClient(url=settings.QDRANT_URL)


async def ensure_collection(client: AsyncQdrantClient, workspace_id: str) -> str:
    """Create workspace-scoped Qdrant collection if it does not already exist."""
    collection = _collection_name(workspace_id)
    existing = [c.name for c in (await client.get_collections()).collections]
    if collection not in existing:
        await client.create_collection(
            collection_name=collection,
            vectors_config=qdrant_models.VectorParams(
                size=VECTOR_SIZE,
                distance=DISTANCE
            )
        )
    return collection


async def upsert_chunks(
    client: AsyncQdrantClient,
    workspace_id: str,
    document_id: str,
    chunks: List[str],
    embeddings: List[List[float]],
) -> int:
    """Store embedded chunks in the workspace's isolated Qdrant collection."""
    collection = await ensure_collection(client, workspace_id)

    points = [
        qdrant_models.PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={
                "workspace_id": workspace_id,
                "document_id": document_id,
                "chunk_index": i,
                "text": chunk,
            }
        )
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings))
    ]

    await client.upsert(collection_name=collection, points=points)
    return len(points)


async def search_vectors(
    client: AsyncQdrantClient,
    workspace_id: str,
    query_vector: List[float],
    top_k: int = 5,
    score_threshold: float = 0.5,
) -> List[dict]:
    """
    Perform similarity search in workspace-isolated collection.
    Only returns results from the authenticated workspace (tenant isolation enforced).
    """
    collection = _collection_name(workspace_id)
    existing = [c.name for c in (await client.get_collections()).collections]
    if collection not in existing:
        return []

    response = await client.query_points(
        collection_name=collection,
        query=query_vector,
        limit=top_k,
        score_threshold=score_threshold,
        with_payload=True,
    )

    return [
        {
            "score": r.score,
            "text": r.payload.get("text", "") if r.payload else "",
            "document_id": r.payload.get("document_id", "") if r.payload else "",
            "chunk_index": r.payload.get("chunk_index", 0) if r.payload else 0,
        }
        for r in response.points
    ]


async def delete_workspace_collection(client: AsyncQdrantClient, workspace_id: str) -> bool:
    """Delete the entire workspace collection (used for cleanup / workspace deletion)."""
    collection = _collection_name(workspace_id)
    existing = [c.name for c in (await client.get_collections()).collections]
    if collection in existing:
        await client.delete_collection(collection)
        return True
    return False

