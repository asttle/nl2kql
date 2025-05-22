from fastapi import FastAPI, HTTPException, BackgroundTasks
from .schemas import NL2KQLRequest, NL2KQLResponse, ExecuteRequest, ExecuteResponse
from .nlp2kql import nl_to_kql, nl_to_kql_detailed
from .kql_executor import execute_kql
from .multi_rag_workflow import multi_rag_workflow
import logging
import asyncio

# Configure basic logging to output to console if not already configured elsewhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(title="NL2KQL API with Multi-RAG Workflow", version="2.0.0")

@app.post("/nl2kql", response_model=NL2KQLResponse)
def convert_nl_to_kql(request: NL2KQLRequest):
    """Convert natural language to KQL using the multi-RAG workflow"""
    try:
        kql = nl_to_kql(
            natural_language=request.natural_language, 
            context=request.context,
            workspace_id=request.workspace_id,
            use_rag=request.use_rag
        )
        return NL2KQLResponse(kql_query=kql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/nl2kql/detailed")
def convert_nl_to_kql_detailed(request: NL2KQLRequest):
    """Convert natural language to KQL with detailed generation information"""
    try:
        result = nl_to_kql_detailed(
            natural_language=request.natural_language,
            context=request.context,
            workspace_id=request.workspace_id,
            use_rag=request.use_rag
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute", response_model=ExecuteResponse)
def convert_and_execute(request: ExecuteRequest):
    """Convert natural language to KQL and execute the query"""
    try:
        logging.info(f"Received /execute request: {request.model_dump()}")
        
        # Generate KQL with detailed information
        kql_result = nl_to_kql_detailed(
            natural_language=request.natural_language,
            context=request.context,
            workspace_id=request.workspace_id,
            use_rag=request.use_rag
        )
        
        kql = kql_result['kql_query']
        logging.info(f"Generated KQL: {kql}")
        
        # Execute the query
        data = execute_kql(kql, 
                          workspace_id=request.workspace_id, 
                          timespan_days=request.timespan_days)
        
        # Enhanced response with generation details
        response_data = {
            "kql_query": kql,
            "data": data,
            "generation_details": {
                "is_valid": kql_result.get('is_valid', True),
                "warnings": kql_result.get('warnings', []),
                "complexity_analysis": kql_result.get('complexity_analysis', {}),
                "context_used": kql_result.get('context_used', {}),
                "rag_workflow_used": kql_result.get('rag_workflow_used', False)
            }
        }
        
        return ExecuteResponse(**response_data)
        
    except ValueError as ve:
        logging.error(f"ValueError in /execute: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Unhandled exception in /execute: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/initialize-rag")
async def initialize_rag_workflow(workspace_id: str, force_refresh: bool = False):
    """Initialize the multi-RAG workflow for a specific workspace"""
    try:
        logging.info(f"Initializing RAG workflow for workspace: {workspace_id}")
        await multi_rag_workflow.initialize_workflow(workspace_id, force_refresh)
        
        status = multi_rag_workflow.get_workflow_status()
        return {
            "message": "RAG workflow initialized successfully",
            "workspace_id": workspace_id,
            "status": status
        }
    except Exception as e:
        logging.error(f"Failed to initialize RAG workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize RAG workflow: {str(e)}")

@app.get("/rag-status")
def get_rag_status():
    """Get the current status of the multi-RAG workflow"""
    try:
        status = multi_rag_workflow.get_workflow_status()
        return status
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/feedback")
def add_feedback(natural_language: str, generated_kql: str, user_feedback: str, corrected_kql: str = None):
    """Add user feedback to improve the system"""
    try:
        multi_rag_workflow.add_feedback(natural_language, generated_kql, user_feedback, corrected_kql)
        return {"message": "Feedback added successfully"}
    except Exception as e:
        logging.error(f"Failed to add feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "features": {
            "multi_rag_workflow": True,
            "kql_validation": True,
            "schema_generation": True,
            "vector_search": True
        }
    }

# Background task to initialize RAG workflow on startup
@app.on_event("startup")
async def startup_event():
    """Initialize the application on startup"""
    logging.info("NL2KQL API with Multi-RAG Workflow starting up...")
    
    # Note: We don't auto-initialize the RAG workflow here because it requires a workspace_id
    # Users should call /initialize-rag endpoint with their workspace_id
    
    logging.info("Application startup completed. Use /initialize-rag to set up the RAG workflow.") 