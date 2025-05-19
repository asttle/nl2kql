from pydantic import BaseModel
from typing import Optional, Any

class NL2KQLRequest(BaseModel):
    natural_language: str
    context: Optional[str] = None

class NL2KQLResponse(BaseModel):
    kql_query: str

class ExecuteRequest(BaseModel):
    natural_language: str
    context: Optional[str] = None
    # Fields for azure-monitor-query
    workspace_id: Optional[str] = None # Changed back from workspace_name
    timespan_days: Optional[int] = 1

class ExecuteResponse(BaseModel):
    kql_query: str
    data: Any 