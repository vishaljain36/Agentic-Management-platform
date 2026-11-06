from typing import List, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()

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
    system_prompt: str
    model_provider: str = "openai"
    model_name: str = "gpt-4o"
    temperature: float = 0.7
    tools: List[str] = Field(default_factory=list)


class AgentResponse(AgentCreate):
    id: str


@router.get("/", response_model=List[AgentResponse])
async def list_agents():
    """Retrieve all configured agents."""
    return list(_mock_agents.values())


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str):
    """Retrieve an agent by its ID."""
    if agent_id not in _mock_agents:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _mock_agents[agent_id]


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_in: AgentCreate):
    """Create a new agent definition."""
    agent_id = f"agent_{len(_mock_agents) + 1}"
    record = agent_in.model_dump()
    record["id"] = agent_id
    _mock_agents[agent_id] = record
    return record

