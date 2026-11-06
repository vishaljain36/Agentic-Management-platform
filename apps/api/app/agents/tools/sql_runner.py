"""Safe SQL query executor with read-only constraint enforcement."""

from langchain_core.tools import tool
import re
from typing import Dict, Any

# Prohibited destructive keywords in read-only analysis mode
DISALLOWED_SQL_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bALTER\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
]


def validate_read_only_sql(query: str) -> bool:
    """Ensure SQL query does not contain destructive mutations."""
    clean = re.sub(r"--.*$", "", query, flags=re.MULTILINE)
    clean = re.sub(r"/\*.*?\*/", "", clean, flags=re.DOTALL)
    for pattern in DISALLOWED_SQL_PATTERNS:
        if re.search(pattern, clean, re.IGNORECASE):
            return False
    return True


@tool
def sql_runner(query: str) -> Dict[str, Any]:
    """Execute a read-only SQL statement against the workspace analytics database.
    
    Args:
        query: SQL SELECT query to execute.
        
    Returns:
        Structured result set or security rejection error.
    """
    if not validate_read_only_sql(query):
        return {
            "success": False,
            "error": "SECURITY_ERROR: Destructive SQL operations (DROP, DELETE, TRUNCATE, ALTER) are disallowed.",
            "rows": [],
        }

    # Simulate query execution with safe mock schema
    return {
        "success": True,
        "query": query.strip(),
        "columns": ["id", "timestamp", "agent_name", "status", "token_count"],
        "rows": [
            ["run-01", "2026-11-05T12:00:00Z", "Researcher", "COMPLETED", 1240],
            ["run-02", "2026-11-05T12:05:00Z", "Evaluator", "COMPLETED", 860],
        ],
        "row_count": 2,
    }

