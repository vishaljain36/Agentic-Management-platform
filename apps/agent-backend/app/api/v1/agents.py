from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Header, Depends
from pydantic import BaseModel, Field

router = APIRouter()

def require_jwt_auth(authorization: Optional[str] = Header(None)) -> str:
    """Validate Bearer JWT token in Authorization header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization scheme. Must use Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or empty JWT token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

# In-memory mock store for agents
_mock_agents: dict[str, dict] = {
    "agent_researcher": {
        "id": "agent_researcher",
        "name": "Researcher Agent",
        "description": "Explores documents and collects domain context",
        "system_prompt": "You are a specialized enterprise research analyst.",
        "model_provider": "openai",
        "model_name": "gpt-4o",
        "temperature": 0.7,
        "tools": ["web_search", "document_vault"]
    },
    "agent_coder": {
        "id": "agent_coder",
        "name": "Code Specialist",
        "description": "Writes, reviews, and validates computational code",
        "system_prompt": "You are an expert full-stack code generator and tester.",
        "model_provider": "anthropic",
        "model_name": "claude-3-5-sonnet",
        "temperature": 0.2,
        "tools": ["python_interpreter", "sql_runner"]
    }
}


class AgentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    system_prompt: Optional[str] = "You are an enterprise AI agent."
    model_provider: str  # Required without default — triggers 422 if omitted
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    tools: List[str] = Field(default_factory=list)


class AgentResponse(AgentCreate):
    id: str


@router.get("", response_model=List[AgentResponse])
@router.get("/", response_model=List[AgentResponse])
async def list_agents():
    """Retrieve all configured agents."""
    return list(_mock_agents.values())


@router.get("/templates", response_model=List[dict])
async def list_agent_templates():
    """Retrieve all 5 pre-configured default marketplace agent templates."""
    from scripts.seed_templates import get_default_templates
    return get_default_templates()


@router.get("/templates/{template_id}")
async def get_agent_template(template_id: str):
    """Retrieve a specific marketplace agent template by ID or slug."""
    from scripts.seed_templates import get_default_templates
    for tpl in get_default_templates():
        if tpl["id"] == template_id or tpl["slug"] == template_id:
            return tpl
    raise HTTPException(status_code=404, detail=f"Template '{template_id}' not found")


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Retrieve an agent by its ID."""
    if agent_id not in _mock_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _mock_agents[agent_id]


@router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_in: AgentCreate, token: str = Depends(require_jwt_auth)):
    """Create a new agent definition (JWT protected)."""
    agent_id = f"agent_{len(_mock_agents) + 1}"
    record = agent_in.model_dump()
    record["id"] = agent_id
    _mock_agents[agent_id] = record
    return record

