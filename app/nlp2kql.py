from .multi_rag_workflow import multi_rag_workflow
from .azure_openai_client import get_kql_from_nl
import logging

logger = logging.getLogger(__name__)

def nl_to_kql(natural_language: str, context: str = None, workspace_id: str = None, use_rag: bool = True) -> str:
    """
    Convert natural language to KQL using either the multi-RAG workflow or basic generation
    
    Args:
        natural_language: The natural language query
        context: Optional additional context
        workspace_id: Optional workspace ID for RAG initialization
        use_rag: Whether to use the multi-RAG workflow (default: True)
    
    Returns:
        Generated KQL query string
    """
    try:
        if use_rag:
            # Use the multi-RAG workflow
            result = multi_rag_workflow.generate_kql_with_rag(
                natural_language=natural_language,
                workspace_id=workspace_id,
                context=context
            )
            return result['kql_query']
        else:
            # Use basic generation
            return get_kql_from_nl(natural_language, context)
            
    except Exception as e:
        logger.error(f"Error in nl_to_kql: {e}")
        # Fallback to basic generation
        return get_kql_from_nl(natural_language, context)

def nl_to_kql_detailed(natural_language: str, context: str = None, workspace_id: str = None, use_rag: bool = True) -> dict:
    """
    Convert natural language to KQL with detailed information about the generation process
    
    Args:
        natural_language: The natural language query
        context: Optional additional context
        workspace_id: Optional workspace ID for RAG initialization
        use_rag: Whether to use the multi-RAG workflow (default: True)
    
    Returns:
        Dictionary with detailed generation information
    """
    try:
        if use_rag:
            # Use the multi-RAG workflow
            return multi_rag_workflow.generate_kql_with_rag(
                natural_language=natural_language,
                workspace_id=workspace_id,
                context=context
            )
        else:
            # Use basic generation with validation
            from .kql_validator import KQLValidator
            validator = KQLValidator()
            
            kql_query = get_kql_from_nl(natural_language, context)
            corrected_kql, warnings, is_valid = validator.validate_and_correct(kql_query)
            complexity_analysis = validator.get_query_complexity_score(corrected_kql)
            
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
                    "context_summary": "Basic generation used"
                },
                "rag_workflow_used": False
            }
            
    except Exception as e:
        logger.error(f"Error in nl_to_kql_detailed: {e}")
        return {
            "kql_query": f"// Error: {str(e)}",
            "original_kql": None,
            "is_valid": False,
            "warnings": [f"Generation failed: {str(e)}"],
            "complexity_analysis": {},
            "context_used": {},
            "rag_workflow_used": False
        } 