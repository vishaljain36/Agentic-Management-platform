"""Test Case BE-UT-04: Celery Background Task Dispatcher & Redis Queue Serialization.

Specification:
1. Configure Celery in eager execution mode (task_always_eager = True).
2. Dispatch background RAG document processing task:
   process_document_rag.delay(doc_id='doc_999', workspace_id='ws_01').
3. Verify JSON serialization of task payload without errors.
4. Confirm Celery worker executes task eagerly and transitions DB status:
   PENDING -> PROCESSING -> COMPLETED.
5. Task return value matches expected vector document metadata.
"""

import json
import pytest
from kombu.serialization import dumps as kombu_dumps, loads as kombu_loads
from workers.celery_app import celery_app, process_document_rag, rag_document_db


def test_be_ut_04_task_payload_json_serialization():
    """Verify that task parameters serialize and deserialize cleanly via Celery's JSON serializer."""
    task_payload = {
        "task_name": "process_document_rag",
        "doc_id": "doc_999",
        "workspace_id": "ws_01",
        "content": "Autonomous Agentic Architecture Blueprint",
        "filename": "blueprint.pdf",
        "metadata": {"author": "AI Architect", "version": "1.0"},
    }

    # Test serialization through kombu JSON serializer used by Celery
    content_type, content_encoding, serialized_bytes = kombu_dumps(task_payload, serializer="json")

    assert content_type == "application/json"
    assert isinstance(serialized_bytes, str) or isinstance(serialized_bytes, bytes)

    # Deserialize and verify byte-for-byte integrity
    deserialized = kombu_loads(serialized_bytes, content_type, content_encoding)
    assert deserialized == task_payload
    assert deserialized["doc_id"] == "doc_999"
    assert deserialized["workspace_id"] == "ws_01"


def test_be_ut_04_celery_eager_dispatch_and_db_status_transitions(eager_celery):
    """Dispatch process_document_rag task in eager mode and verify PENDING -> PROCESSING -> COMPLETED."""
    doc_id = "doc_999"
    workspace_id = "ws_01"

    # Reset in-memory database record
    rag_document_db.pop(doc_id, None)

    # Dispatch task via .delay() (eager execution invokes immediately)
    async_result = process_document_rag.delay(
        doc_id=doc_id,
        workspace_id=workspace_id,
        content="Deep research into autonomous multi-agent state machines.",
        filename="rag_specs.txt",
        metadata={"priority": "high"},
    )

    # 1. Verify task completed successfully
    assert async_result.successful() is True
    assert async_result.state == "SUCCESS"

    result_data = async_result.result
    assert result_data is not None
    assert result_data["doc_id"] == doc_id
    assert result_data["workspace_id"] == workspace_id
    assert result_data["status"] == "COMPLETED"
    assert result_data["chunks_indexed"] == 4
    assert result_data["dimensions"] == 1536
    assert result_data["metadata"]["priority"] == "high"

    # 2. Verify database status progression: PENDING -> PROCESSING -> COMPLETED
    assert doc_id in rag_document_db
    doc_record = rag_document_db[doc_id]

    assert doc_record["status"] == "COMPLETED"
    assert doc_record["history"] == ["PENDING", "PROCESSING", "COMPLETED"]

