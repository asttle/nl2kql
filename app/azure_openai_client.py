import requests
from .config import settings

def get_kql_from_nl(natural_language: str, context: str = None) -> str:
    print("AOAI Client settings:", settings.model_dump())
    # Updated system prompt to be less aggressive with projecting columns
    system_message_content = (
        "You are an assistant that ONLY returns valid Kusto Query Language (KQL) queries. "
        "Do not return greetings or explanations. Only output the KQL query. "
        "If projecting columns, ensure they are common and likely to exist for the described log type. "
        "If unsure about specific columns, project only very common columns like TimeGenerated and LogMessage, or omit the 'project' operator entirely."
    )
    if context:
        system_message_content += f" Use the following context if provided: {context}"

    messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": f"{natural_language}"}
    ] 
    headers = {
        "Authorization": f"Bearer {settings.azure_openai_key}",
        "Content-Type": "application/json"
    }
    data = {
        "messages": messages,
        "temperature": 0.2, # Reduced temperature for more deterministic KQL
        "top_p": 1.0,
        "frequency_penalty": 0.0,
        "presence_penalty": 0.0,
        "model": "gpt-4.1-2025-04-14"
    }
    response = requests.post(
        f"{settings.azure_openai_endpoint}/openai/deployments/gpt-4.1-2025-04-14/chat/completions?api-version=2024-12-01-preview",
        headers=headers,
        json=data
    )
    response.raise_for_status()
    kql = response.json()["choices"][0]["message"]["content"].strip()
    # Remove potential markdown backticks from KQL
    if kql.startswith("```kusto"):
        kql = kql[len("```kusto"):].strip()
    if kql.startswith("```"):
        kql = kql[len("```"):].strip()
    if kql.endswith("```"):
        kql = kql[:-len("```")].strip()
    return kql 