"""Qdrant Cloud vector collection initialization script.

Checks or creates the `workspace_documents` collection with:
- 1536-dimensional vectors (compatible with OpenAI text-embedding-3-small or ada-002)
- Cosine distance metric
- Optimized HNSW graph indexing:
  - m: 16 (number of edges per node)
  - ef_construct: 100 (construction search depth)
  - on_disk: False (in-memory fast graph)
- Payload schema indexes for multi-tenant workspace filtering:
  - `workspace_id`: keyword index
  - `document_id`: keyword index
"""

import sys
import os
import argparse
from typing import Optional

# Ensure repository path is accessible
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from config.production import production_settings


def init_qdrant_collection(
    url: Optional[str] = None,
    api_key: Optional[str] = None,
    collection_name: Optional[str] = None,
    dim: Optional[int] = None,
) -> bool:
    """Initialize Qdrant collection with production HNSW parameters."""
    target_url = url or production_settings.QDRANT_URL
    target_key = api_key or production_settings.QDRANT_API_KEY
    target_collection = collection_name or production_settings.QDRANT_COLLECTION_NAME
    vector_size = dim or production_settings.QDRANT_VECTOR_DIM

    print(f"[Qdrant Init] Connecting to cluster: {target_url}")
    print(f"[Qdrant Init] Target collection: '{target_collection}' (dim={vector_size})")

    # Connect to Qdrant (works for Qdrant Cloud TLS or local)
    client = QdrantClient(url=target_url, api_key=target_key, timeout=15)

    # Check existing collections
    collections_response = client.get_collections()
    existing_names = [col.name for col in collections_response.collections]

    if target_collection in existing_names:
        print(f"[Qdrant Init] Collection '{target_collection}' already exists.")
        info = client.get_collection(collection_name=target_collection)
        print(f"[Qdrant Init] Current status: {info.status}, vectors_count={info.vectors_count}")
        return True

    print(f"[Qdrant Init] Collection '{target_collection}' not found. Creating collection...")

    # Configure Vector parameters with HNSW graph indexing
    vectors_config = qmodels.VectorParams(
        size=vector_size,
        distance=qmodels.Distance.COSINE,
        on_disk=False,
        hnsw_config=qmodels.HnswConfigDiff(
            m=16,
            ef_construct=100,
            full_scan_threshold=10000,
        ),
    )

    client.create_collection(
        collection_name=target_collection,
        vectors_config=vectors_config,
        optimizers_config=qmodels.OptimizersConfigDiff(
            indexing_threshold=10000,
        ),
    )

    # Create payload indexes for multi-tenant query acceleration
    print("[Qdrant Init] Creating payload keyword index for 'workspace_id'...")
    client.create_payload_index(
        collection_name=target_collection,
        field_name="workspace_id",
        field_schema=qmodels.PayloadSchemaType.KEYWORD,
    )

    print("[Qdrant Init] Creating payload keyword index for 'document_id'...")
    client.create_payload_index(
        collection_name=target_collection,
        field_name="document_id",
        field_schema=qmodels.PayloadSchemaType.KEYWORD,
    )

    print(f"[Qdrant Init] Successfully created and indexed collection '{target_collection}'!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize production Qdrant vector collection")
    parser.add_argument("--url", help="Qdrant Cloud endpoint URL", default=None)
    parser.add_argument("--api-key", help="Qdrant API Key", default=None)
    parser.add_argument("--collection", help="Collection name", default=None)
    parser.add_argument("--dim", type=int, help="Vector dimension", default=None)

    args = parser.parse_args()

    try:
        success = init_qdrant_collection(
            url=args.url,
            api_key=args.api_key,
            collection_name=args.collection,
            dim=args.dim,
        )
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[Qdrant Init] Error: {e}", file=sys.stderr)
        sys.exit(1)

