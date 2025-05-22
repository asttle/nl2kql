import re
import json
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict, Counter
import logging
from .azure_openai_client import get_kql_from_nl
from .kql_executor import execute_kql
import requests
from .config import settings

logger = logging.getLogger(__name__)

class SchemaGenerator:
    """Generates schemas and field descriptions from data source logs"""
    
    def __init__(self):
        self.common_log_tables = [
            "SecurityEvent", "Syslog", "Event", "Heartbeat", "Perf", "Alert",
            "AzureActivity", "SigninLogs", "AuditLogs", "AppServiceHTTPLogs",
            "ContainerLog", "KubeEvents", "InsightsMetrics", "VMConnection",
            "SecurityAlert", "SecurityIncident", "ThreatIntelligenceIndicator"
        ]
    
    def discover_tables(self, workspace_id: str, timespan_days: int = 7) -> List[str]:
        """Discover available tables in the workspace"""
        try:
            # Query to get all tables with data in the last N days
            discovery_query = f"""
            union withsource=TableName *
            | where TimeGenerated > ago({timespan_days}d)
            | summarize Count=count() by TableName
            | where Count > 0
            | order by Count desc
            | project TableName
            """
            
            result = execute_kql(discovery_query, workspace_id=workspace_id, timespan_days=timespan_days)
            
            tables = []
            if result and isinstance(result, list):
                for table_data in result:
                    if 'rows' in table_data:
                        for row in table_data['rows']:
                            if row and len(row) > 0:
                                tables.append(row[0])
            
            logger.info(f"Discovered {len(tables)} tables with data")
            return tables
            
        except Exception as e:
            logger.warning(f"Failed to discover tables: {e}. Using common tables.")
            return self.common_log_tables
    
    def extract_table_schema(self, table_name: str, workspace_id: str, timespan_days: int = 7) -> Dict[str, Any]:
        """Extract schema information for a specific table"""
        try:
            # Query to get column information and sample data
            schema_query = f"""
            {table_name}
            | where TimeGenerated > ago({timespan_days}d)
            | take 100
            | getschema
            """
            
            result = execute_kql(schema_query, workspace_id=workspace_id, timespan_days=timespan_days)
            
            schema_info = {
                "table_name": table_name,
                "columns": [],
                "sample_data": []
            }
            
            if result and isinstance(result, list):
                for table_data in result:
                    if 'columns' in table_data and 'rows' in table_data:
                        columns = table_data['columns']
                        rows = table_data['rows']
                        
                        for row in rows:
                            if len(row) >= 2:  # getschema returns ColumnName, ColumnType
                                column_info = {
                                    "name": row[0],
                                    "type": row[1],
                                    "ordinal": row[2] if len(row) > 2 else 0
                                }
                                schema_info["columns"].append(column_info)
            
            # Get sample data for the table
            sample_query = f"""
            {table_name}
            | where TimeGenerated > ago({timespan_days}d)
            | take 10
            """
            
            sample_result = execute_kql(sample_query, workspace_id=workspace_id, timespan_days=timespan_days)
            if sample_result and isinstance(sample_result, list):
                for table_data in sample_result:
                    if 'rows' in table_data:
                        schema_info["sample_data"] = table_data['rows'][:5]  # Limit to 5 samples
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to extract schema for table {table_name}: {e}")
            return {"table_name": table_name, "columns": [], "sample_data": []}
    
    def generate_field_descriptions(self, schema_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate AI-powered descriptions for fields based on schema and sample data"""
        field_descriptions = []
        
        table_name = schema_info["table_name"]
        columns = schema_info["columns"]
        sample_data = schema_info.get("sample_data", [])
        
        for column in columns:
            field_name = column["name"]
            data_type = column["type"]
            
            # Extract sample values for this column
            sample_values = []
            if sample_data and len(sample_data) > 0:
                column_index = next((i for i, col in enumerate(columns) if col["name"] == field_name), None)
                if column_index is not None:
                    for row in sample_data:
                        if len(row) > column_index and row[column_index] is not None:
                            sample_values.append(str(row[column_index]))
            
            # Generate AI description
            description = self._generate_ai_description(table_name, field_name, data_type, sample_values)
            
            field_descriptions.append({
                "table_name": table_name,
                "field_name": field_name,
                "data_type": data_type,
                "description": description,
                "sample_values": sample_values[:10]  # Keep first 10 samples
            })
        
        return field_descriptions
    
    def _generate_ai_description(self, table_name: str, field_name: str, data_type: str, sample_values: List[str]) -> str:
        """Generate AI-powered description for a field"""
        try:
            # Create a prompt for generating field description
            sample_values_str = ", ".join(sample_values[:5]) if sample_values else "No samples available"
            
            prompt = f"""
            Generate a concise, technical description for this log analytics field:
            
            Table: {table_name}
            Field: {field_name}
            Data Type: {data_type}
            Sample Values: {sample_values_str}
            
            Provide a 1-2 sentence description explaining what this field represents, its purpose, and any relevant context for KQL queries. Focus on practical usage for log analysis.
            """
            
            headers = {
                "Authorization": f"Bearer {settings.azure_openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": [
                    {"role": "system", "content": "You are a log analytics expert. Generate concise, technical field descriptions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 150,
                "model": "gpt-4.1-2025-04-14"
            }
            
            response = requests.post(
                f"{settings.azure_openai_endpoint}/openai/deployments/gpt-4.1-2025-04-14/chat/completions?api-version=2024-12-01-preview",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                description = response.json()["choices"][0]["message"]["content"].strip()
                return description
            else:
                logger.warning(f"Failed to generate AI description for {field_name}: {response.status_code}")
                return self._generate_fallback_description(table_name, field_name, data_type)
                
        except Exception as e:
            logger.warning(f"Error generating AI description for {field_name}: {e}")
            return self._generate_fallback_description(table_name, field_name, data_type)
    
    def _generate_fallback_description(self, table_name: str, field_name: str, data_type: str) -> str:
        """Generate a fallback description based on common patterns"""
        field_lower = field_name.lower()
        
        # Common field patterns
        if "time" in field_lower or "date" in field_lower:
            return f"Timestamp field indicating when the {table_name} event occurred."
        elif "id" in field_lower:
            return f"Unique identifier for the {table_name} record."
        elif "name" in field_lower:
            return f"Name or identifier field in the {table_name} table."
        elif "status" in field_lower or "state" in field_lower:
            return f"Status or state information for the {table_name} event."
        elif "message" in field_lower or "description" in field_lower:
            return f"Descriptive message or details for the {table_name} event."
        elif "count" in field_lower or "number" in field_lower:
            return f"Numeric count or quantity field in the {table_name} table."
        elif "source" in field_lower:
            return f"Source information for the {table_name} event."
        elif "type" in field_lower:
            return f"Type or category classification for the {table_name} event."
        else:
            return f"Field in the {table_name} table of type {data_type}."
    
    def extract_field_values(self, table_name: str, field_name: str, workspace_id: str, timespan_days: int = 7, limit: int = 100) -> List[str]:
        """Extract sample values for a specific field"""
        try:
            values_query = f"""
            {table_name}
            | where TimeGenerated > ago({timespan_days}d)
            | where isnotempty({field_name})
            | summarize count() by {field_name}
            | order by count_ desc
            | take {limit}
            | project {field_name}
            """
            
            result = execute_kql(values_query, workspace_id=workspace_id, timespan_days=timespan_days)
            
            values = []
            if result and isinstance(result, list):
                for table_data in result:
                    if 'rows' in table_data:
                        for row in table_data['rows']:
                            if row and len(row) > 0 and row[0] is not None:
                                values.append(str(row[0]))
            
            return values
            
        except Exception as e:
            logger.error(f"Failed to extract values for {table_name}.{field_name}: {e}")
            return []
    
    def generate_table_description(self, table_name: str, schema_info: Dict[str, Any]) -> str:
        """Generate a description for the entire table"""
        try:
            columns_info = ", ".join([f"{col['name']} ({col['type']})" for col in schema_info['columns'][:10]])
            
            prompt = f"""
            Generate a concise description for this log analytics table:
            
            Table Name: {table_name}
            Key Columns: {columns_info}
            
            Provide a 2-3 sentence description explaining what this table contains, what types of events or data it stores, and its primary use cases in log analytics and KQL queries.
            """
            
            headers = {
                "Authorization": f"Bearer {settings.azure_openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": [
                    {"role": "system", "content": "You are a log analytics expert. Generate concise table descriptions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 200,
                "model": "gpt-4.1-2025-04-14"
            }
            
            response = requests.post(
                f"{settings.azure_openai_endpoint}/openai/deployments/gpt-4.1-2025-04-14/chat/completions?api-version=2024-12-01-preview",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                description = response.json()["choices"][0]["message"]["content"].strip()
                return description
            else:
                return f"Log analytics table containing {table_name} events and related data."
                
        except Exception as e:
            logger.warning(f"Error generating table description for {table_name}: {e}")
            return f"Log analytics table containing {table_name} events and related data." 