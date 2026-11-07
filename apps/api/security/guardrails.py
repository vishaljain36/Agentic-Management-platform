"""LLM Input Guardrails, Prompt Injection Shielding & Pydantic Tool Schemas.

Implements Section 2.1 of Production Launch Blueprint:
- Prompt Injection & System Instruction Override Shielding
- Jailbreak & Roleplay Evasion Detection (NeMo Guardrails Compatible)
- Strict Pydantic Schema Validation on Tool Inputs & Outputs
"""

import re
from typing import Optional, Dict, Any, List, Type
from pydantic import BaseModel, Field, ValidationError, field_validator

# ---------------------------------------------------------------------------
# Custom Guardrail Exceptions
# ---------------------------------------------------------------------------


class PromptSecurityViolation(Exception):
    """Raised when an input prompt violates injection, jailbreak, or safety guardrails."""

    def __init__(self, message: str, category: str, pattern: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.category = category
        self.pattern = pattern


class ToolSchemaValidationError(Exception):
    """Raised when tool inputs or outputs fail strict Pydantic validation."""

    def __init__(self, message: str, tool_name: str, details: Any):
        super().__init__(message)
        self.message = message
        self.tool_name = tool_name
        self.details = details


# ---------------------------------------------------------------------------
# Prompt Injection & Jailbreak Signatures
# ---------------------------------------------------------------------------

INJECTION_PATTERNS = [
    # System Token & Template Injection Attempts (highest precedence)
    (r"<\|im_start\|>", "TEMPLATE_DELIMITER_INJECTION"),
    (r"<\|system\|>", "TEMPLATE_DELIMITER_INJECTION"),
    (r"\[INST\]", "TEMPLATE_DELIMITER_INJECTION"),
    (r"<<SYS>>", "TEMPLATE_DELIMITER_INJECTION"),
    (r"\[SYSTEM\s+PROMPT\]", "TEMPLATE_DELIMITER_INJECTION"),

    # System Instruction Overrides
    (r"(?i)\bignore\s+(?:all\s+)?(?:previous|prior|above|existing|\s+)*\s*(?:instructions|prompts|rules|commands|directives)\b", "INSTRUCTION_OVERRIDE"),
    (r"(?i)\bdisregard\s+(?:all\s+)?(?:previous|prior|system|existing|\s+)*\s*(?:instructions|directives|prompts|rules|commands)\b", "INSTRUCTION_OVERRIDE"),
    (r"(?i)\bforget\s+(?:all\s+)?(?:your|previous|prior|system|\s+)*\s*(?:rules|instructions|prompts|directives)\b", "INSTRUCTION_OVERRIDE"),
    (r"(?i)\boverride\s+(?:the\s+)?(?:system|safety|core|\s+)*\s*(?:prompt|protocol|guidelines|instructions)\b", "INSTRUCTION_OVERRIDE"),

    # Jailbreak Personas & Modes
    (r"(?i)\b(?:you\s+are\s+now|act\s+as)\s+(?:DAN|Do\s+Anything\s+Now)\b", "JAILBREAK_PERSONA"),
    (r"(?i)\bdeveloper\s+mode\s+(?:is\s+)?(?:enabled|active|on)\b", "JAILBREAK_PERSONA"),
    (r"(?i)\bjailbreak(?:\s+mode|\s+prompt)?\b", "JAILBREAK_PERSONA"),
    (r"(?i)\bunrestricted\s+(?:mode|AI|assistant)\b", "JAILBREAK_PERSONA"),

    # Sensitive System Prompt Exfiltration Attempts
    (r"(?i)\b(?:reveal|show|print|dump|repeat|output)\s+(?:your\s+)?(?:initial|original|secret|hidden|system|\s+)*\s*(?:prompt|instructions|directives)\b", "DATA_EXFILTRATION"),
    (r"(?i)\bwhat\s+(?:was|is)\s+the\s+text\s+(?:above|prior\s+to\s+this)\b", "DATA_EXFILTRATION"),
]


def scan_prompt_security(prompt: str) -> Dict[str, Any]:
    """Scan an input prompt against NeMo-style prompt injection & jailbreak rules.
    
    Returns:
        dict: {
            "is_safe": bool,
            "category": Optional[str],
            "pattern": Optional[str],
            "reason": Optional[str]
        }
    """
    if not prompt or not prompt.strip():
        return {"is_safe": True, "category": None, "pattern": None, "reason": None}

    clean_prompt = prompt.strip()

    for pattern_regex, category in INJECTION_PATTERNS:
        match = re.search(pattern_regex, clean_prompt)
        if match:
            reason = f"Security Violation: Blocked {category.lower().replace('_', ' ')} attempt."
            return {
                "is_safe": False,
                "category": category,
                "pattern": match.group(0),
                "reason": reason,
            }

    return {"is_safe": True, "category": None, "pattern": None, "reason": None}


def enforce_prompt_guardrails(prompt: str) -> str:
    """Validate prompt safety. Raises PromptSecurityViolation if rejected."""
    result = scan_prompt_security(prompt)
    if not result["is_safe"]:
        raise PromptSecurityViolation(
            message=result["reason"],
            category=result["category"],
            pattern=result["pattern"],
        )
    return prompt


# ---------------------------------------------------------------------------
# Strict Pydantic Tool Input & Output Schemas
# ---------------------------------------------------------------------------


class CodeRunnerInput(BaseModel):
    """Pydantic schema for code sandbox execution tool."""
    code: str = Field(..., min_length=1, max_length=50000, description="Python script code to execute")
    timeout_seconds: int = Field(default=30, ge=1, le=60, description="Execution timeout in seconds")
    memory_limit_mb: int = Field(default=512, ge=64, le=1024, description="Memory limit in megabytes")
    cpu_cap: float = Field(default=1.0, ge=0.1, le=2.0, description="vCPU cap")

    @field_validator("code")
    @classmethod
    def validate_code_safety(cls, v: str) -> str:
        # Reject obvious unauthorized network socket operations
        if "import socket" in v or "from socket import" in v:
            raise ValueError("Direct socket operations are disallowed in tool code execution.")
        return v


class VectorSearchInput(BaseModel):
    """Pydantic schema for RAG vector search tool."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query string")
    workspace_id: str = Field(..., min_length=1, max_length=128, description="Target workspace tenant identifier")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of results to retrieve")
    score_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Similarity score threshold")


class SqlRunnerInput(BaseModel):
    """Pydantic schema for SQL query executor tool."""
    query: str = Field(..., min_length=4, max_length=5000, description="SQL SELECT query to execute")

    @field_validator("query")
    @classmethod
    def validate_read_only(cls, v: str) -> str:
        disallowed = [r"\bDROP\b", r"\bDELETE\b", r"\bTRUNCATE\b", r"\bALTER\b", r"\bGRANT\b", r"\bREVOKE\b"]
        for pattern in disallowed:
            if re.search(pattern, v, re.IGNORECASE):
                raise ValueError(f"Destructive SQL operations are prohibited in read-only analyzer mode.")
        return v.strip()


class WebSearchInput(BaseModel):
    """Pydantic schema for web search tool."""
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Max search results")


TOOL_INPUT_SCHEMAS: Dict[str, Type[BaseModel]] = {
    "code_runner": CodeRunnerInput,
    "sandbox_executor": CodeRunnerInput,
    "vector_search": VectorSearchInput,
    "sql_runner": SqlRunnerInput,
    "web_search": WebSearchInput,
}


def validate_tool_payload(tool_name: str, payload: Dict[str, Any]) -> BaseModel:
    """Validate tool input against strict Pydantic schema model."""
    schema_cls = TOOL_INPUT_SCHEMAS.get(tool_name)
    if not schema_cls:
        # If no custom schema registered, allow payload through
        return payload

    try:
        return schema_cls(**payload)
    except ValidationError as e:
        raise ToolSchemaValidationError(
            message=f"Invalid payload for tool '{tool_name}': {e}",
            tool_name=tool_name,
            details=e.errors(),
        )
