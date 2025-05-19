# NL2KQL: Natural Language to Kusto Query Language

A modern Python application that converts natural language to Kusto Query Language (KQL), executes queries against Azure Log Analytics Workspaces (across subscriptions), and provides a beautiful Chainlit UI. Powered by Azure OpenAI.

---

## ✨ Features
- **Natural Language to KQL**: Use Azure OpenAI to translate plain English to KQL.
- **Query Execution**: Run KQL queries on your Azure Log Analytics workspace (not ADX).
- **Multi-Subscription Support**: Uses your Azure CLI profile to access any workspace in any subscription.
- **Chainlit UI**: Chat interface for easy interaction.
- **REST API**: FastAPI backend for programmatic access.
- **Modern Python stack**: Pydantic, FastAPI, Chainlit, Azure SDKs.

---

## 🏗️ Architecture
```
[Chainlit UI] <-> [FastAPI Backend] <-> [Azure OpenAI] <-> [Azure Log Analytics]
```
- Modular SDK in `app/`
- UI in `chainlit_app/`
- API endpoints: `/nl2kql`, `/execute`

---

## 🚀 Quickstart

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/nlp2kql.git
cd nlp2kql
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file and fill in your Azure details:
```env
# Azure OpenAI
azure_openai_endpoint=
azure_openai_key=

# (Optional) Default Log Analytics Workspace
log_analytics_workspace_id=
# (Optional) Default Azure Subscription
azure_subscription_id=
```
- You can override the workspace per request via the API.
- The app uses your current `az login` context for authentication.

### 3. Run the Backend
```bash
uvicorn app.main:app --reload
```

### 4. Run the Chainlit UI
```bash
chainlit run chainlit_app/chainlit_app.py
```

---

## 🧪 Testing
```bash
pytest
```

---

## 📁 Folder Structure
```
app/
  __init__.py
  main.py
  schemas.py
  nlp2kql.py
  kql_executor.py
  azure_openai_client.py
  config.py
chainlit_app/
  __init__.py
  chainlit_app.py
tests/
  test_nlp2kql.py
requirements.txt
.env
README.md
```

---

## 🛡️ Security & Best Practices
- **Never commit secrets**: Use `.env` for local dev, Azure Key Vault for prod.
- **Pydantic** for all data validation.
- **Async-ready**: FastAPI and Chainlit are async.
- **Azure Authentication**: Uses your Azure CLI/DefaultAzureCredential for workspace access.

---

## 📚 References
- [Azure OpenAI Service](https://learn.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Azure Monitor Query Python SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/monitor-query-readme?view=azure-python)
- [Chainlit Docs](https://docs.chainlit.io/)
- [FastAPI](https://fastapi.tiangolo.com/)

---

## 📝 License
MIT 