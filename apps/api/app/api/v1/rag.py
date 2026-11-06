import uuid
from typing import List, Optional
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, status
from pydantic import BaseModel

from app.memory.document_parser import parse_document, chunk_text
from app.memory.embeddings import embed_texts
from app.memory.qdrant_client import (
    get_qdrant_client,
    upsert_chunks,
    search_vectors,
)

router = APIRouter()


class IndexResponse(BaseModel):
    document_id: str
    workspace_id: str
    filename: str
    chunks_indexed: int


class SearchRequest(BaseModel):
    query: str
    workspace_id: str
    top_k: int = 5
    score_threshold: float = 0.5


class SearchResult(BaseModel):
    score: float
    text: str
    document_id: str
    chunk_index: int


@router.post("/index", response_model=IndexResponse, status_code=status.HTTP_201_CREATED)
async def index_document(
    workspace_id: str = Form(...),
    file: UploadFile = File(...),
):
    """
    Upload, parse, chunk, embed, and index a document into the workspace's
    Qdrant collection. Supports PDF, DOCX, and TXT/MD formats.
    Tenant isolation is enforced — each workspace gets its own collection.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # 1. Parse document to raw text
    try:
        raw_text = parse_document(file.filename, content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found in document")

    # 2. Chunk text
    chunks = chunk_text(raw_text, chunk_size=512, overlap=64)
    if not chunks:
        raise HTTPException(status_code=422, detail="Document chunking produced no output")

    # 3. Generate embeddings
    embeddings = embed_texts(chunks)

    # 4. Upsert into Qdrant with workspace isolation
    document_id = str(uuid.uuid4())
    client = await get_qdrant_client()
    try:
        indexed = await upsert_chunks(
            client=client,
            workspace_id=workspace_id,
            document_id=document_id,
            chunks=chunks,
            embeddings=embeddings,
        )
    finally:
        await client.close()

    return IndexResponse(
        document_id=document_id,
        workspace_id=workspace_id,
        filename=file.filename,
        chunks_indexed=indexed,
    )


@router.post("/search", response_model=List[SearchResult])
async def search_documents(req: SearchRequest):
    """
    Perform semantic similarity search in the authenticated workspace's vector store.
    Tenant isolation enforced — query cannot cross workspace collection boundaries.
    """
    query_embeddings = embed_texts([req.query])
    if not query_embeddings:
        raise HTTPException(status_code=500, detail="Embedding generation failed")

    client = await get_qdrant_client()
    try:
        results = await search_vectors(
            client=client,
            workspace_id=req.workspace_id,
            query_vector=query_embeddings[0],
            top_k=req.top_k,
            score_threshold=req.score_threshold,
        )
    finally:
        await client.close()

    return [
        SearchResult(
            score=r["score"],
            text=r["text"],
            document_id=r["document_id"],
            chunk_index=r["chunk_index"],
        )
        for r in results
    ]

