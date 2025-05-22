from pydantic import BaseModel
from typing import Optional, Any, List, Dict

class NL2KQLRequest(BaseModel):
    natural_language: str
    context: Optional[str] = None
    workspace_id: Optional[str] = None
    use_rag: Optional[bool] = True

class NL2KQLResponse(BaseModel):
    kql_query: str

class ExecuteRequest(BaseModel):
    natural_language: str
    context: Optional[str] = None
    workspace_id: Optional[str] = None
    timespan_days: Optional[int] = 1
    use_rag: Optional[bool] = True

class GenerationDetails(BaseModel):
    is_valid: bool
    warnings: List[str]
    complexity_analysis: Dict[str, Any]
    context_used: Dict[str, Any]
    rag_workflow_used: bool

class ExecuteResponse(BaseModel):
    kql_query: str
    data: Any
    generation_details: Optional[GenerationDetails] = None

class RAGStatusResponse(BaseModel):
    initialized: bool
    vector_store_stats: Dict[str, int]
    total_entries: int
    components_loaded: Dict[str, bool]

class FeedbackRequest(BaseModel):
    natural_language: str
    generated_kql: str
    user_feedback: str
    corrected_kql: Optional[str] = None 