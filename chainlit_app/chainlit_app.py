import chainlit as cl
import requests
import os
import pandas as pd

API_URL = os.getenv("NL2KQL_API_URL", "http://localhost:8000")

import openlit

openlit.init(otlp_endpoint="http://localhost:4318", service_name )

@cl.on_message
async def main(message: cl.Message):
    nl = message.content
    # Call the /execute endpoint
    response = requests.post(f"{API_URL}/execute", json={"natural_language": nl})
    if response.status_code == 200:
        data = response.json()
        kql = data.get("kql_query", "")
        result = data.get("data", [])
        await cl.Message(
            content=f"**KQL Query:**\n```kusto\n{kql}\n```\n**Results:**\n{result}",
            author="NL2KQL Bot"
        ).send()
        print("DATA:", data)
        print("KQL:", kql)
        print("RESULT:", result)
        if not kql.strip():
            await cl.Message(
                content=f"Error: The model did not return a valid KQL query. Please provide a query or a natural language request to convert to KQL.",
                author="NL2KQL Bot"
            ).send()
        else:
            for table in result:
                if not table["columns"]:
                    await cl.Message(
                        content=f"**Table: {table['name']}**\nNo columns returned.",
                        author="NL2KQL Bot"
                    ).send()
                    continue
                df = pd.DataFrame(table["rows"], columns=table["columns"])
                await cl.Message(
                    content=f"**KQL Query:**\n```kusto\n{kql}\n```\n**Table: {table['name']}**",
                    author="NL2KQL Bot",
                    elements=[cl.Dataframe(name=table["name"], dataframe=df)]
                ).send()
    else:
        await cl.Message(
            content=f"Error: {response.text}",
            author="NL2KQL Bot"
        ).send()