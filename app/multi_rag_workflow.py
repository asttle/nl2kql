from typing import List, Dict, Any, Optional
import logging
import asyncio
from .vector_store import VectorStore
from .schema_generator import SchemaGenerator
from .schema_refiner import SchemaRefiner
from .kql_validator import KQLValidator
from .azure_openai_client import get_kql_from_nl
import requests
from .config import settings

logger = logging.getLogger(__name__)

class MultiRAGWorkflow:
    """Main orchestrator for the multi-RAG workflow for NL2KQL generation"""
    
    def __init__(self):
        self.vector_store = VectorStore()
        self.schema_generator = SchemaGenerator()
        self.schema_refiner = SchemaRefiner()
        self.kql_validator = KQLValidator()
        self._initialized = False
        
    async def initialize_workflow(self, workspace_id: str, force_refresh: bool = False):
        """Initialize the workflow by populating vector stores with schema data"""
        if self._initialized and not force_refresh:
            logger.info("Multi-RAG workflow already initialized")
            return
            
        logger.info("Initializing multi-RAG workflow...")
        
        try:
            # Check if we already have data in vector stores
            stats = self.vector_store.get_collection_stats()
            if not force_refresh and all(count > 0 for count in stats.values()):
                logger.info(f"Vector stores already populated: {stats}")
                self._initialized = True
                return
            
            # Discover tables in the workspace
            logger.info("Discovering tables in workspace...")
            tables = self.schema_generator.discover_tables(workspace_id)
            logger.info(f"Found {len(tables)} tables: {tables[:10]}...")  # Log first 10
            
            # Process each table to extract schema and generate descriptions
            all_field_descriptions = []
            all_field_values = []
            all_schemas = []
            
            # Limit to top tables to avoid overwhelming the system
            tables_to_process = tables[:20]  # Process top 20 tables
            
            for i, table_name in enumerate(tables_to_process):
                logger.info(f"Processing table {i+1}/{len(tables_to_process)}: {table_name}")
                
                try:
                    # Extract schema information
                    schema_info = self.schema_generator.extract_table_schema(table_name, workspace_id)
                    
                    if not schema_info['columns']:
                        logger.warning(f"No columns found for table {table_name}, skipping")
                        continue
                    
                    # Generate field descriptions
                    field_descriptions = self.schema_generator.generate_field_descriptions(schema_info)
                    all_field_descriptions.extend(field_descriptions)
                    
                    # Extract field values for key fields
                    for field_desc in field_descriptions[:10]:  # Limit to first 10 fields per table
                        field_name = field_desc['field_name']
                        sample_values = self.schema_generator.extract_field_values(
                            table_name, field_name, workspace_id, limit=50
                        )
                        
                        if sample_values:
                            all_field_values.append({
                                'table_name': table_name,
                                'field_name': field_name,
                                'sample_values': sample_values
                            })
                    
                    # Generate table description
                    table_description = self.schema_generator.generate_table_description(table_name, schema_info)
                    
                    # Create schema entry
                    schema_entry = {
                        'table_name': table_name,
                        'description': table_description,
                        'schema': self._format_schema(schema_info['columns'])
                    }
                    all_schemas.append(schema_entry)
                    
                except Exception as e:
                    logger.error(f"Error processing table {table_name}: {e}")
                    continue
            
            # Populate vector stores
            logger.info("Populating vector stores...")
            
            if all_field_descriptions:
                self.vector_store.add_field_descriptions(all_field_descriptions)
            
            if all_field_values:
                self.vector_store.add_field_values(all_field_values)
            
            if all_schemas:
                self.vector_store.add_schemas(all_schemas)
            
            # Add some ground truth examples
            self._add_ground_truth_examples()
            
            # Log final stats
            final_stats = self.vector_store.get_collection_stats()
            logger.info(f"Vector stores populated: {final_stats}")
            
            self._initialized = True
            logger.info("Multi-RAG workflow initialization completed")
            
        except Exception as e:
            logger.error(f"Failed to initialize multi-RAG workflow: {e}")
            raise
    
    def _format_schema(self, columns: List[Dict[str, Any]]) -> str:
        """Format column information into a readable schema string"""
        schema_parts = []
        for col in columns:
            schema_parts.append(f"{col['name']} ({col['type']})")
        return ", ".join(schema_parts)
    
    def _add_ground_truth_examples(self):
        """Add some ground truth NL2KQL examples to the vector store"""
        ground_truth_examples = [
            {
                "natural_language": "Show me all security events from the last 24 hours",
                "kql_query": "SecurityEvent\n| where TimeGenerated > ago(24h)\n| take 100",
                "description": "Basic security event query with time filter"
            },
            {
                "natural_language": "Count failed login attempts by user",
                "kql_query": "SecurityEvent\n| where TimeGenerated > ago(7d)\n| where EventID == 4625\n| summarize FailedLogins = count() by Account\n| order by FailedLogins desc",
                "description": "Aggregation query for failed login analysis"
            },
            {
                "natural_language": "Show Azure activity logs for resource creation",
                "kql_query": "AzureActivity\n| where TimeGenerated > ago(1d)\n| where OperationName contains \"Create\"\n| project TimeGenerated, Caller, OperationName, ResourceGroup, Resource",
                "description": "Azure activity filtering and projection"
            },
            {
                "natural_language": "Find processes with high CPU usage",
                "kql_query": "Perf\n| where TimeGenerated > ago(1h)\n| where ObjectName == \"Processor\" and CounterName == \"% Processor Time\"\n| where CounterValue > 80\n| project TimeGenerated, Computer, CounterValue",
                "description": "Performance monitoring query"
            },
            {
                "natural_language": "Show recent sign-in failures",
                "kql_query": "SigninLogs\n| where TimeGenerated > ago(24h)\n| where ResultType != \"0\"\n| project TimeGenerated, UserPrincipalName, AppDisplayName, ResultType, ResultDescription",
                "description": "Sign-in log analysis for failures"
            }
        ]
        
        self.vector_store.add_ground_truth_pairs(ground_truth_examples)
    
    def generate_kql_with_rag(self, natural_language: str, workspace_id: str = None, context: str = None) -> Dict[str, Any]:
        """Generate KQL using the multi-RAG workflow"""
        
        # Ensure workflow is initialized
        if not self._initialized:
            logger.warning("Multi-RAG workflow not initialized, using basic generation")
            return self._fallback_generation(natural_language, context)
        
        try:
            logger.info(f"Generating KQL with multi-RAG for: {natural_language}")
            
            # Step 1: Retrieve relevant context using similarity search
            logger.info("Step 1: Retrieving relevant context...")
            relevant_fields = self.vector_store.search_relevant_fields(natural_language, n_results=15)
            relevant_values = self.vector_store.search_relevant_values(natural_language, n_results=8)
            relevant_schemas = self.vector_store.search_relevant_schemas(natural_language, n_results=5)
            similar_queries = self.vector_store.search_similar_queries(natural_language, n_results=5)
            
            logger.info(f"Retrieved: {len(relevant_fields)} fields, {len(relevant_values)} value sets, "
                       f"{len(relevant_schemas)} schemas, {len(similar_queries)} similar queries")
            
            # Step 2: Refine and process the retrieved context
            logger.info("Step 2: Refining context...")
            refined_context = self.schema_refiner.refine_context(
                natural_language, relevant_fields, relevant_values, relevant_schemas, similar_queries
            )
            
            # Step 3: Generate KQL with enhanced context
            logger.info("Step 3: Generating KQL with enhanced context...")
            enhanced_context = self._build_enhanced_context(refined_context, context)
            kql_query = self._generate_kql_with_context(natural_language, enhanced_context)
            
            # Step 4: Validate and correct the generated KQL
            logger.info("Step 4: Validating and correcting KQL...")
            available_tables = [table['table_name'] for table in refined_context['refined_tables']]
            corrected_kql, warnings, is_valid = self.kql_validator.validate_and_correct(kql_query, available_tables)
            
            # Step 5: Get complexity analysis
            complexity_analysis = self.kql_validator.get_query_complexity_score(corrected_kql)
            
            result = {
                "kql_query": corrected_kql,
                "original_kql": kql_query if kql_query != corrected_kql else None,
                "is_valid": is_valid,
                "warnings": warnings,
                "complexity_analysis": complexity_analysis,
                "context_used": {
                    "tables_considered": len(refined_context['refined_tables']),
                    "fields_considered": len(relevant_fields),
                    "similar_queries_found": len(similar_queries),
                    "context_summary": refined_context['context_summary']
                },
                "rag_workflow_used": True
            }
            
            logger.info(f"KQL generation completed. Valid: {is_valid}, Warnings: {len(warnings)}")
            return result
            
        except Exception as e:
            logger.error(f"Error in multi-RAG workflow: {e}")
            # Fallback to basic generation
            return self._fallback_generation(natural_language, context)
    
    def _build_enhanced_context(self, refined_context: Dict[str, Any], original_context: str = None) -> str:
        """Build enhanced context string for KQL generation"""
        context_parts = []
        
        # Add original context if provided
        if original_context:
            context_parts.append(f"Original Context: {original_context}")
        
        # Add refined instructions
        context_parts.append(refined_context['instructions'])
        
        # Add table information
        if refined_context['refined_tables']:
            context_parts.append("\nDetailed Table Information:")
            for table in refined_context['refined_tables'][:3]:  # Top 3 tables
                table_info = f"\nTable: {table['table_name']}"
                if table['description']:
                    table_info += f"\nDescription: {table['description']}"
                
                # Add field information
                if table['fields']:
                    field_info = []
                    for field in table['fields'][:8]:  # Top 8 fields
                        field_desc = f"  - {field['field_name']} ({field['data_type']}): {field['description']}"
                        field_info.append(field_desc)
                    table_info += f"\nKey Fields:\n" + "\n".join(field_info)
                
                # Add sample values
                if table['sample_values']:
                    values_info = []
                    for value_info in table['sample_values'][:3]:  # Top 3 fields with values
                        sample_vals = ", ".join(str(v) for v in value_info['sample_values'][:5])
                        values_info.append(f"  - {value_info['field_name']}: {sample_vals}")
                    table_info += f"\nSample Values:\n" + "\n".join(values_info)
                
                context_parts.append(table_info)
        
        # Add similar query patterns
        if refined_context['query_patterns']:
            context_parts.append("\nSimilar Query Examples:")
            for pattern in refined_context['query_patterns'][:2]:  # Top 2 patterns
                if pattern['kql_query']:
                    context_parts.append(f"Example: {pattern['similar_nl']}")
                    context_parts.append(f"KQL: {pattern['kql_query']}")
        
        return "\n".join(context_parts)
    
    def _generate_kql_with_context(self, natural_language: str, enhanced_context: str) -> str:
        """Generate KQL using Azure OpenAI with enhanced context"""
        try:
            system_prompt = """You are an expert KQL (Kusto Query Language) assistant. Generate ONLY valid KQL queries based on the provided context and natural language request.

Rules:
1. Return ONLY the KQL query, no explanations or markdown
2. Use only tables and fields mentioned in the context
3. Always include TimeGenerated filters when appropriate
4. Use proper KQL syntax and operators
5. Ensure field names match exactly as provided in the context
6. Prefer simple, efficient queries over complex ones"""

            user_prompt = f"""Natural Language Request: {natural_language}

Context Information:
{enhanced_context}

Generate a valid KQL query that answers the request using the provided context."""

            headers = {
                "Authorization": f"Bearer {settings.azure_openai_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,  # Low temperature for more deterministic results
                "max_tokens": 500,
                "model": "gpt-4.1-2025-04-14"
            }
            
            response = requests.post(
                f"{settings.azure_openai_endpoint}/openai/deployments/gpt-4.1-2025-04-14/chat/completions?api-version=2024-12-01-preview",
                headers=headers,
                json=data
            )
            
            if response.status_code == 200:
                kql = response.json()["choices"][0]["message"]["content"].strip()
                
                # Clean up the response
                if kql.startswith("```kusto"):
                    kql = kql[len("```kusto"):].strip()
                if kql.startswith("```kql"):
                    kql = kql[len("```kql"):].strip()
                if kql.startswith("```"):
                    kql = kql[len("```"):].strip()
                if kql.endswith("```"):
                    kql = kql[:-len("```")].strip()
                
                return kql
            else:
                logger.error(f"Azure OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"Azure OpenAI API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating KQL with context: {e}")
            # Fallback to basic generation
            return get_kql_from_nl(natural_language, enhanced_context)
    
    def _fallback_generation(self, natural_language: str, context: str = None) -> Dict[str, Any]:
        """Fallback to basic KQL generation when RAG workflow fails"""
        logger.info("Using fallback KQL generation")
        
        try:
            kql_query = get_kql_from_nl(natural_language, context)
            corrected_kql, warnings, is_valid = self.kql_validator.validate_and_correct(kql_query)
            complexity_analysis = self.kql_validator.get_query_complexity_score(corrected_kql)
            
            return {
                "kql_query": corrected_kql,
                "original_kql": kql_query if kql_query != corrected_kql else None,
                "is_valid": is_valid,
                "warnings": warnings,
                "complexity_analysis": complexity_analysis,
                "context_used": {
                    "tables_considered": 0,
                    "fields_considered": 0,
                    "similar_queries_found": 0,
                    "context_summary": "Fallback generation used"
                },
                "rag_workflow_used": False
            }
        except Exception as e:
            logger.error(f"Fallback generation also failed: {e}")
            return {
                "kql_query": "// Error: Could not generate KQL query",
                "original_kql": None,
                "is_valid": False,
                "warnings": [f"Generation failed: {str(e)}"],
                "complexity_analysis": {},
                "context_used": {},
                "rag_workflow_used": False
            }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """Get the current status of the multi-RAG workflow"""
        stats = self.vector_store.get_collection_stats()
        
        return {
            "initialized": self._initialized,
            "vector_store_stats": stats,
            "total_entries": sum(stats.values()),
            "components_loaded": {
                "vector_store": True,
                "schema_generator": True,
                "schema_refiner": True,
                "kql_validator": True
            }
        }
    
    def add_feedback(self, natural_language: str, generated_kql: str, user_feedback: str, corrected_kql: str = None):
        """Add user feedback to improve the system (for future implementation)"""
        # This could be used to add new ground truth examples based on user feedback
        if corrected_kql and user_feedback.lower() in ['good', 'correct', 'accurate']:
            try:
                feedback_entry = {
                    "natural_language": natural_language,
                    "kql_query": corrected_kql,
                    "description": f"User-validated query: {user_feedback}"
                }
                self.vector_store.add_ground_truth_pairs([feedback_entry])
                logger.info("Added user feedback to ground truth examples")
            except Exception as e:
                logger.error(f"Failed to add user feedback: {e}")

# Global instance
multi_rag_workflow = MultiRAGWorkflow() 