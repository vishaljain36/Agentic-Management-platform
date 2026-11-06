from functools import lru_cache
from typing import List


@lru_cache(maxsize=1)
def _get_embedder():
    """Lazy-load the FastEmbed model (cached for process lifetime)."""
    from fastembed import TextEmbedding
    return TextEmbedding(model_name="BAAI/bge-small-en-v1.5")


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of text strings using BAAI/bge-small-en-v1.5 (384-dim vectors).
    Falls back to zero vectors if fastembed is unavailable.
    """
    if not texts:
        return []
    embedder = _get_embedder()
    embeddings = list(embedder.embed(texts))
    return [e.tolist() for e in embeddings]

