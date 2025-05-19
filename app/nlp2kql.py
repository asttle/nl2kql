from .azure_openai_client import get_kql_from_nl

def nl_to_kql(natural_language: str, context: str = None) -> str:
    return get_kql_from_nl(natural_language, context) 