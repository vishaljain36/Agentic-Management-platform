from typing import List, Optional, Annotated
from langchain_core.tools import tool

from app.memory.embeddings import embed_texts
from app.memory.qdrant_client import get_qdrant_client, search_vectors


@tool
async def vector_search(
    query: Annotated[str, "The semantic search query to find relevant document chunks"],
    workspace_id: Annotated[str, "The workspace ID to scope the vector search to (tenant isolation)"],
    top_k: Annotated[int, "Maximum number of results to return"] = 5,
    score_threshold: Annotated[float, "Minimum similarity score (0–1) for results"] = 0.5,
) -> List[dict]:
    """
    Search the workspace knowledge vault for semantically similar document chunks.
    Uses BAAI/bge-small-en-v1.5 embeddings against workspace-isolated Qdrant collections.
    Results are strictly scoped to the specified workspace — cross-workspace access is impossible.
    
    Returns a list of matching chunks with similarity scores, document IDs, and text content.
    """
    query_embeddings = embed_texts([query])
    if not query_embeddings:
        return []

    client = await get_qdrant_client()
    try:
        results = await search_vectors(
            client=client,
            workspace_id=workspace_id,
            query_vector=query_embeddings[0],
            top_k=top_k,
            score_threshold=score_threshold,
        )
    finally:
        await client.close()

    return results

