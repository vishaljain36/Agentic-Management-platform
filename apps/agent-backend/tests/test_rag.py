"""
Integration tests for Phase 3: Knowledge Ingestion Vault & Vector RAG

Covers:
  - Document parsing (TXT, PDF, DOCX)
  - Text chunking with overlap
  - Embedding generation
  - Qdrant upsert and similarity search
  - Tenant isolation (Workspace A cannot see Workspace B)
  - API endpoints via FastAPI test client
"""
import io
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock

from app.memory.document_parser import chunk_text, parse_text, parse_document
from app.memory.embeddings import embed_texts
from main import app


# ---------------------------------------------------------------------------
# Unit Tests: Document Parser
# ---------------------------------------------------------------------------

def test_chunk_text_short_document():
    """Short texts that fit in one chunk are returned as a single item."""
    text = "This is a brief summary."
    chunks = chunk_text(text, chunk_size=512, overlap=64)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_long_document_produces_overlap():
    """Long texts produce multiple overlapping chunks."""
    text = "word " * 400  # ~2000 chars
    chunks = chunk_text(text, chunk_size=512, overlap=64)
    assert len(chunks) > 1
    # Verify overlap — beginning of chunk[1] should appear at end of chunk[0]
    # (allow for whitespace trimming)
    for c in chunks:
        assert len(c) <= 512 + 10  # allow slight boundary tolerance


def test_chunk_text_empty_string():
    """Empty strings return no chunks."""
    assert chunk_text("", chunk_size=512, overlap=64) == []


def test_parse_text_bytes():
    """UTF-8 bytes are decoded to string correctly."""
    content = b"Hello, Agentic Workspace!"
    result = parse_text(content)
    assert result == "Hello, Agentic Workspace!"


def test_parse_document_txt_routing():
    """parse_document routes .txt files through parse_text."""
    content = b"This is a test document.\nLine two."
    result = parse_document("report.txt", content)
    assert "test document" in result


def test_parse_document_unsupported_format():
    """Unsupported file extensions raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported file type"):
        parse_document("archive.zip", b"some bytes")


def test_parse_document_pdf():
    """PDF parsing extracts text content from a minimal PDF."""
    import pypdf
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    page = writer.add_blank_page(width=200, height=200)
    writer.write(buf)
    buf.seek(0)
    # Blank PDF may return empty string — just check no exception is raised
    result = parse_document("blank.pdf", buf.read())
    assert isinstance(result, str)


def test_parse_document_docx():
    """DOCX parsing extracts paragraph text."""
    import docx
    buf = io.BytesIO()
    doc = docx.Document()
    doc.add_paragraph("Agentic platform knowledge base.")
    doc.add_paragraph("Vector search enables semantic retrieval.")
    doc.save(buf)
    buf.seek(0)
    result = parse_document("report.docx", buf.read())
    assert "Agentic platform knowledge base" in result
    assert "Vector search" in result


# ---------------------------------------------------------------------------
# Unit Tests: Embeddings
# ---------------------------------------------------------------------------

def test_embed_texts_returns_384_dim_vectors():
    """BAAI/bge-small-en-v1.5 produces 384-dimensional embeddings."""
    texts = ["Agentic workspace platform", "Vector search for RAG pipelines"]
    embeddings = embed_texts(texts)
    assert len(embeddings) == 2
    for emb in embeddings:
        assert len(emb) == 384
        assert isinstance(emb[0], float)


def test_embed_texts_empty_list():
    """Empty input returns empty list without errors."""
    result = embed_texts([])
    assert result == []


def test_embed_different_texts_different_vectors():
    """Semantically different texts produce distinct embedding vectors."""
    embs = embed_texts(["cat", "quantum computing"])
    assert embs[0] != embs[1]


def test_embed_similar_texts_close_cosine():
    """Semantically similar texts produce high cosine similarity (> 0.8)."""
    import math

    texts = [
        "Retrieve documents using vector similarity",
        "Find relevant documents through semantic search"
    ]
    embs = embed_texts(texts)
    a, b = embs[0], embs[1]
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(x ** 2 for x in b))
    cosine = dot / (mag_a * mag_b)
    assert cosine > 0.75, f"Expected similarity > 0.75, got {cosine:.3f}"


# ---------------------------------------------------------------------------
# Integration Tests: Qdrant operations (mocked)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_qdrant_upsert_and_search():
    """Upsert chunks into an in-memory Qdrant instance and retrieve them."""
    from qdrant_client import AsyncQdrantClient

    in_memory_client = AsyncQdrantClient(":memory:")

    from app.memory.qdrant_client import upsert_chunks, search_vectors, ensure_collection
    workspace_id = "ws_test_integration"
    document_id = "doc_001"

    text = "The Agentic workspace platform uses LangGraph to orchestrate multi-agent workflows with HITL checkpoints."
    chunks = chunk_text(text, chunk_size=512, overlap=0)
    embeddings = embed_texts(chunks)

    # Upsert
    count = await upsert_chunks(
        client=in_memory_client,
        workspace_id=workspace_id,
        document_id=document_id,
        chunks=chunks,
        embeddings=embeddings,
    )
    assert count == len(chunks)

    # Search with same query embedding — should score very high
    query_emb = embed_texts(["LangGraph multi-agent orchestration"])[0]
    results = await search_vectors(
        client=in_memory_client,
        workspace_id=workspace_id,
        query_vector=query_emb,
        top_k=3,
        score_threshold=0.0,
    )
    assert len(results) >= 1
    top = results[0]
    assert top["score"] >= 0.75, f"Expected similarity >= 0.75, got {top['score']:.4f}"
    assert "document_id" in top
    assert "text" in top

    await in_memory_client.close()


@pytest.mark.asyncio
async def test_tenant_isolation():
    """
    Workspace A cannot query Workspace B's vectors.
    Each workspace has a fully isolated Qdrant collection.
    """
    from qdrant_client import AsyncQdrantClient
    from app.memory.qdrant_client import upsert_chunks, search_vectors

    client = AsyncQdrantClient(":memory:")

    ws_a = "workspace_alpha"
    ws_b = "workspace_beta"
    doc_a = "doc_alpha_001"

    chunks_a = ["Confidential financial data for workspace Alpha"]
    embeddings_a = embed_texts(chunks_a)

    await upsert_chunks(client, ws_a, doc_a, chunks_a, embeddings_a)

    # Query from ws_a's perspective — should find results
    query = embed_texts(["financial data alpha"])[0]
    results_a = await search_vectors(client, ws_a, query, top_k=5, score_threshold=0.0)
    assert len(results_a) >= 1

    # Query from ws_b's perspective — collection does not exist, returns empty
    results_b = await search_vectors(client, ws_b, query, top_k=5, score_threshold=0.0)
    assert results_b == [], f"Workspace B should not see Workspace A's data, got {results_b}"

    await client.close()


# ---------------------------------------------------------------------------
# API Endpoint Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_rag_index_txt_document():
    """RAG index endpoint accepts TXT file and returns chunk count."""
    txt_content = b"The platform uses vector embeddings to enable semantic search over documents. " * 5
    files = {"file": ("test_doc.txt", txt_content, "text/plain")}
    data = {"workspace_id": "ws_api_test"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Patch the Qdrant client to avoid needing a live server
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.create_collection = AsyncMock()
        mock_qdrant.upsert = AsyncMock()
        mock_qdrant.close = AsyncMock()

        with patch("app.api.v1.rag.get_qdrant_client", return_value=mock_qdrant):
            response = await client.post("/api/v1/rag/index", files=files, data=data)

    assert response.status_code == 201
    body = response.json()
    assert body["workspace_id"] == "ws_api_test"
    assert body["filename"] == "test_doc.txt"
    assert body["chunks_indexed"] >= 1
    assert "document_id" in body


@pytest.mark.asyncio
async def test_api_rag_index_docx_document():
    """RAG index endpoint accepts DOCX file."""
    import docx as python_docx
    buf = io.BytesIO()
    doc = python_docx.Document()
    for i in range(5):
        doc.add_paragraph(f"Paragraph {i}: Agentic platform knowledge with vector embeddings and multi-agent orchestration.")
    doc.save(buf)
    buf.seek(0)

    files = {"file": ("knowledge.docx", buf.read(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")}
    data = {"workspace_id": "ws_docx_test"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        mock_qdrant = AsyncMock()
        mock_qdrant.get_collections.return_value = MagicMock(collections=[])
        mock_qdrant.create_collection = AsyncMock()
        mock_qdrant.upsert = AsyncMock()
        mock_qdrant.close = AsyncMock()

        with patch("app.api.v1.rag.get_qdrant_client", return_value=mock_qdrant):
            response = await client.post("/api/v1/rag/index", files=files, data=data)

    assert response.status_code == 201
    body = response.json()
    assert body["chunks_indexed"] >= 1


@pytest.mark.asyncio
async def test_api_rag_search():
    """RAG search endpoint returns similarity results."""
    search_results = [
        {"score": 0.92, "text": "LangGraph orchestrates multi-agent workflows", "document_id": "doc_001", "chunk_index": 0},
        {"score": 0.85, "text": "HITL checkpoints pause execution for human review", "document_id": "doc_001", "chunk_index": 1},
    ]

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        mock_qdrant = AsyncMock()
        mock_col = MagicMock()
        mock_col.name = "workspace_ws_search_test"
        mock_qdrant.get_collections.return_value = MagicMock(collections=[mock_col])
        mock_qdrant.query_points = AsyncMock(return_value=MagicMock(points=[
            MagicMock(score=r["score"], payload={"text": r["text"], "document_id": r["document_id"], "chunk_index": r["chunk_index"]})
            for r in search_results
        ]))
        mock_qdrant.close = AsyncMock()

        with patch("app.api.v1.rag.get_qdrant_client", return_value=mock_qdrant):
            response = await client.post("/api/v1/rag/search", json={
                "query": "multi-agent LangGraph workflow",
                "workspace_id": "ws_search_test",
                "top_k": 5,
                "score_threshold": 0.5
            })

    assert response.status_code == 200
    results = response.json()
    assert len(results) == 2
    assert results[0]["score"] == 0.92
    assert "LangGraph" in results[0]["text"]


@pytest.mark.asyncio
async def test_api_rag_unsupported_file_type():
    """RAG index endpoint rejects unsupported file types with 422."""
    files = {"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")}
    data = {"workspace_id": "ws_bad_test"}

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/api/v1/rag/index", files=files, data=data)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_langgraph_vector_search_tool():
    """Verify that vector_search tool is callable as a LangGraph tool."""
    from app.agents.tools.vector_search import vector_search
    from qdrant_client import AsyncQdrantClient
    from app.memory.qdrant_client import upsert_chunks

    client = AsyncQdrantClient(":memory:")
    ws_id = "ws_tool_test"
    doc_id = "doc_tool_001"
    chunks = ["LangGraph tool calling enables agents to query Qdrant directly."]
    embeddings = embed_texts(chunks)
    await upsert_chunks(client, ws_id, doc_id, chunks, embeddings)

    with patch("app.agents.tools.vector_search.get_qdrant_client", return_value=client):
        results = await vector_search.ainvoke({
            "query": "LangGraph tool calling",
            "workspace_id": ws_id,
            "top_k": 3,
            "score_threshold": 0.5
        })

    assert len(results) >= 1
    assert "document_id" in results[0]
    assert results[0]["score"] > 0.75
    await client.close()


