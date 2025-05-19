from fastapi import FastAPI, HTTPException
from .schemas import NL2KQLRequest, NL2KQLResponse, ExecuteRequest, ExecuteResponse
from .nlp2kql import nl_to_kql
from .kql_executor import execute_kql
import logging

# Configure basic logging to output to console if not already configured elsewhere
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(title="NL2KQL API")

@app.post("/nl2kql", response_model=NL2KQLResponse)
def convert_nl_to_kql(request: NL2KQLRequest):
    try:
        kql = nl_to_kql(request.natural_language, request.context)
        return NL2KQLResponse(kql_query=kql)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/execute", response_model=ExecuteResponse)
def convert_and_execute(request: ExecuteRequest):
    try:
        logging.info(f"Received /execute request: {request.model_dump()}")
        kql = nl_to_kql(request.natural_language, request.context)
        logging.info(f"Generated KQL: {kql}")
        
        # Pass workspace_id and timespan_days directly from the validated request model
        data = execute_kql(kql, 
                           workspace_id=request.workspace_id, 
                           timespan_days=request.timespan_days)
        return ExecuteResponse(kql_query=kql, data=data)
    except ValueError as ve: # Catch specific ValueError from kql_executor for bad config
        logging.error(f"ValueError in /execute: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logging.error(f"Unhandled exception in /execute: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) 