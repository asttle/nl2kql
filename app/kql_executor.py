from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.core.exceptions import HttpResponseError
from .config import settings
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)

_credential = None
_logs_client = None # Renaming back from _log_analytics_client for clarity

def get_logs_client(): # Renaming back
    global _credential, _logs_client
    if _logs_client is None:
        _credential = DefaultAzureCredential() # DefaultAzureCredential will use AZURE_SUBSCRIPTION_ID from env if set
        _logs_client = LogsQueryClient(_credential)
        logger.info("Initialized LogsQueryClient with DefaultAzureCredential.")
    return _logs_client

def execute_kql(kql_query: str, 
                workspace_id: str = None, # Changed back from individual params
                timespan_days: int = 1):
    
    client = get_logs_client()
    
    # Use workspace_id from request or fallback to settings
    ws_id = workspace_id or settings.log_analytics_workspace_id

    if not ws_id:
        error_msg = "Log Analytics Workspace ID is not provided. Please set it in .env or include in the request."
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info(f"Executing KQL on Workspace ID: {ws_id}")
    logger.info(f"KQL Query: {kql_query}")
    logger.info(f"Timespan: {timespan_days} day(s)")

    try:
        response = client.query_workspace(
            workspace_id=ws_id, 
            query=kql_query, 
            timespan=timedelta(days=timespan_days)
        )
        logger.info(f"Log Analytics API Response Status: {response.status}")

        if response.status == LogsQueryStatus.SUCCESS:
            logger.info(f"Log Analytics API Response Tables (raw): {response.tables}")
            processed_tables = []
            if response.tables:
                for table in response.tables:
                    if hasattr(table, 'name') and hasattr(table, 'columns') and hasattr(table, 'rows'):
                        processed_tables.append({
                            "name": table.name,
                            "columns": [col.name for col in table.columns if hasattr(col, 'name')],
                            "rows": table.rows
                        })
                    else:
                        logger.warning(f"Skipping malformed table object in response: {table}")
            else:
                logger.info("Query returned successfully but with no tables/data.")
            return processed_tables
        elif response.status == LogsQueryStatus.PARTIAL:
            logger.warning(f"Log Analytics query returned partial data. Error: {response.partial_error}")
            processed_tables = []
            if response.partial_data:
                 for table in response.partial_data:
                    if hasattr(table, 'name') and hasattr(table, 'columns') and hasattr(table, 'rows'):
                        processed_tables.append({
                            "name": table.name,
                            "columns": [col.name for col in table.columns if hasattr(col, 'name')],
                            "rows": table.rows
                        })
                    else:
                        logger.warning(f"Skipping malformed table object in partial_data: {table}")
            return {"data": processed_tables, "error": str(response.partial_error), "status": "PartialSuccess"}
        else: # LogsQueryStatus.FAILURE
            logger.error(f"Log Analytics query failed. Error details: {response.error}")
            return {"error": str(response.error), "status": "Failure"}

    except HttpResponseError as e:
        logger.error(f"HttpResponseError during Log Analytics query for workspace {ws_id}: {e.message}", exc_info=True)
        raise # Re-raise to let FastAPI handle it as a 500
    except Exception as e:
        logger.error(f"Unexpected error during Log Analytics query for workspace {ws_id}: {e}", exc_info=True)
        raise # Re-raise for FastAPI to handle 