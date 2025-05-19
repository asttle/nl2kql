import chainlit as cl
import requests
import os

API_URL = os.getenv("NL2KQL_API_URL", "http://localhost:8000")

@cl.on_message
async def main(message: cl.Message):
    nl = message.content
    # Call the /execute endpoint
    response = requests.post(f"{API_URL}/execute", json={"natural_language": nl})
    if response.status_code == 200:
        data = response.json()
        kql = data["kql_query"]
        result = data["data"]
        if not kql.strip().endswith(";") and "|" not in kql:
            await cl.Message(
                content=f"Error: The model did not return a valid KQL query. Please provide a query or a natural language request to convert to KQL.",
                author="NL2KQL Bot"
            ).send()
        else:
            await cl.Message(
                content=f"**KQL Query:**\n```kusto\n{kql}\n```\n**Results:**\n{result}",
                author="NL2KQL Bot"
            ).send()
    else:
        await cl.Message(
            content=f"Error: {response.text}",
            author="NL2KQL Bot"
        ).send()