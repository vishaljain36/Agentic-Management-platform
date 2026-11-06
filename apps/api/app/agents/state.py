from typing import TypedDict, Annotated, Sequence, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_step: str
    requires_approval: bool
    approval_data: Dict[str, Any]
    output: str
    run_id: Optional[str]
    total_tokens: Optional[int]
    cost_usd: Optional[float]

