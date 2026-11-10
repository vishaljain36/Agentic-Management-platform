"""Test Case BE-UT-01: FastAPI Pydantic Request Validation & Auth JWT Middleware.

Specification:
1. Send POST request to `/api/v1/agents` without Authorization header -> 401 Unauthorized.
2. Send POST request with valid JWT header but missing required field `model_provider` -> 422 Unprocessable Entity.
3. Detail highlights missing field `model_provider`.
4. Valid payload returns 201 Created.
"""

import pytest
import httpx


@pytest.mark.asyncio
async def test_be_ut_01_missing_auth_header_returns_401(async_client: httpx.AsyncClient):
    """Attempting to create an agent without Authorization header returns HTTP 401 Unauthorized."""
    payload = {
        "name": "Test Agent",
        "system_prompt": "You are a test agent.",
        "model_provider": "openai",
        "model_name": "gpt-4o",
    }
    response = await async_client.post("/api/v1/agents", json=payload)
    assert response.status_code == 401
    assert "Authorization" in response.json()["detail"]


@pytest.mark.asyncio
async def test_be_ut_01_invalid_auth_scheme_returns_401(async_client: httpx.AsyncClient):
    """Supplying a non-Bearer or empty Authorization header returns HTTP 401 Unauthorized."""
    response = await async_client.post(
        "/api/v1/agents",
        json={"name": "Test Agent", "model_provider": "openai"},
        headers={"Authorization": "Basic dXNlcjpwYXNz"},
    )
    assert response.status_code == 401
    assert "Bearer" in response.json()["detail"]


@pytest.mark.asyncio
async def test_be_ut_01_missing_model_provider_returns_422(async_client: httpx.AsyncClient):
    """Supplying valid JWT header but omitting required model_provider triggers 422 Unprocessable Entity."""
    # Body missing required field 'model_provider'
    payload = {
        "name": "Test Agent",
    }
    headers = {
        "Authorization": "Bearer jwt_mock_valid_session_token_999",
    }

    response = await async_client.post("/api/v1/agents", json=payload, headers=headers)
    assert response.status_code == 422

    error_data = response.json()
    assert "detail" in error_data
    # Verify the validation error specifically highlights the missing model_provider field
    missing_fields = [
        err["loc"][-1]
        for err in error_data["detail"]
        if err.get("type") == "missing"
    ]
    assert "model_provider" in missing_fields


@pytest.mark.asyncio
async def test_be_ut_01_valid_payload_returns_201_created(async_client: httpx.AsyncClient):
    """Complete and authenticated payload returns HTTP 201 Created and persists agent record."""
    payload = {
        "name": "Market Analyst Agent",
        "description": "Performs financial market analysis",
        "system_prompt": "You are an equities research analyst.",
        "model_provider": "anthropic",
        "model_name": "claude-3-5-sonnet",
        "temperature": 0.3,
        "tools": ["web_search", "python_interpreter"],
    }
    headers = {
        "Authorization": "Bearer jwt_mock_valid_session_token_999",
    }

    response = await async_client.post("/api/v1/agents", json=payload, headers=headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Market Analyst Agent"
    assert data["model_provider"] == "anthropic"
    assert "id" in data

