# NL2KQL Multi-RAG Workflow System

A sophisticated Natural Language to KQL (Kusto Query Language) conversion system with multi-RAG (Retrieval-Augmented Generation) workflow for Azure Log Analytics.

## 🚀 Features

### Core Capabilities
- **Multi-RAG Workflow**: Advanced retrieval system using vector embeddings for context-aware KQL generation
- **Schema-Aware Generation**: Automatically discovers and uses actual workspace schemas
- **KQL Validation & Correction**: Built-in syntax validation and error correction
- **Complexity Analysis**: Query performance impact assessment
- **Fallback Mechanisms**: Graceful degradation when components fail

### Multi-RAG Architecture Components

1. **Vector Store** (`app/vector_store.py`)
   - ChromaDB-based persistent vector storage
   - Sentence transformer embeddings (with MockEmbedder fallback)
   - Four specialized collections: field descriptions, field values, schemas, ground truth pairs

2. **Schema Generator** (`app/schema_generator.py`)
   - Automatic table discovery from Log Analytics workspaces
   - AI-powered field description generation
   - Sample value extraction for context enrichment

3. **Schema Refiner** (`app/schema_refiner.py`)
   - Context prioritization and relevance scoring
   - Query pattern extraction from similar examples
   - Enhanced instruction generation for LLM

4. **KQL Validator** (`app/kql_validator.py`)
   - Syntax validation and correction
   - Common mistake fixes (operators, functions, table names)
   - Query complexity analysis and performance impact assessment

5. **Multi-RAG Orchestrator** (`app/multi_rag_workflow.py`)
   - Coordinates the entire workflow
   - 5-step generation process with fallback mechanisms
   - Feedback integration for continuous improvement

## 📋 Prerequisites

- Python 3.8+
- Azure Log Analytics workspace access
- Azure OpenAI service access
- Required environment variables (see Configuration section)

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd nlp2kql
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Fix SSL and test setup**
   ```bash
   python scripts/fix_ssl_and_download_model.py
   ```

## ⚙️ Configuration

Create a `.env` file in the project root:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-openai-resource.openai.azure.com/
AZURE_OPENAI_KEY=your-api-key-here

# Azure Log Analytics (optional, can be provided per request)
AZURE_WORKSPACE_ID=your-workspace-id
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

## 🚀 Quick Start

### 1. Start the API Server

```bash
# Set SSL environment variables (if needed)
export CURL_CA_BUNDLE=$(python -c "import certifi; print(certifi.where())")
export REQUESTS_CA_BUNDLE=$(python -c "import certifi; print(certifi.where())")

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Test Basic Functionality

```bash
# Health check
curl -X GET "http://localhost:8000/health"

# Basic NL2KQL conversion
curl -X POST "http://localhost:8000/nl2kql" \
  -H "Content-Type: application/json" \
  -d '{"natural_language": "Show me security events from the last 24 hours", "use_rag": false}'
```

### 3. Initialize RAG Workflow (Optional)

```bash
# Initialize RAG for a specific workspace
curl -X POST "http://localhost:8000/initialize-rag?workspace_id=YOUR_WORKSPACE_ID&force_refresh=false"

# Check RAG status
curl -X GET "http://localhost:8000/rag-status"
```

## 📚 API Endpoints

### Core Endpoints

- **POST /nl2kql** - Basic NL2KQL conversion
- **POST /nl2kql/detailed** - Detailed conversion with validation info
- **POST /execute** - Convert and execute KQL query
- **GET /health** - Health check

### RAG Workflow Endpoints

- **POST /initialize-rag** - Initialize RAG workflow for workspace
- **GET /rag-status** - Get RAG workflow status
- **POST /feedback** - Add user feedback for improvement

### Example Request/Response

```bash
# Detailed conversion request
curl -X POST "http://localhost:8000/nl2kql/detailed" \
  -H "Content-Type: application/json" \
  -d '{
    "natural_language": "Show me failed login attempts in the last week",
    "workspace_id": "your-workspace-id",
    "use_rag": true
  }'
```

```json
{
  "kql_query": "SecurityEvent\n| where TimeGenerated > ago(7d)\n| where EventID == 4625\n| project TimeGenerated, Account, Computer, FailureReason",
  "is_valid": true,
  "warnings": [],
  "complexity_analysis": {
    "operations": {"filters": 2, "projections": 1, "aggregations": 0},
    "complexity_score": 3,
    "performance_impact": "Low",
    "has_time_filter": true
  },
  "context_used": {
    "tables_considered": 1,
    "fields_considered": 8,
    "similar_queries_found": 2,
    "context_summary": "SecurityEvent table with authentication fields"
  },
  "rag_workflow_used": true
}
```

## 🔧 Data Preparation

Use the data preparation script to initialize RAG workflow:

```bash
# Show what would be processed (dry run)
python scripts/prepare_data.py --workspace-id YOUR_WORKSPACE_ID --dry-run

# Initialize RAG workflow
python scripts/prepare_data.py --workspace-id YOUR_WORKSPACE_ID

# Force refresh existing data
python scripts/prepare_data.py --workspace-id YOUR_WORKSPACE_ID --force-refresh
```

## 🎨 Enhanced User Interface

### Chainlit Web App with RAG Workflow Visualization

The enhanced Chainlit app now provides detailed visibility into the Multi-RAG workflow process:

#### **Startup Experience**
- **RAG Status Check**: Automatically checks if the RAG workflow is initialized
- **Knowledge Base Info**: Shows number of entries loaded (tables, fields, examples)
- **Initialization Guidance**: Provides instructions if RAG workflow needs setup

#### **Query Processing Visualization**
When you submit a natural language query, the app shows:

1. **🔄 Processing Indicator**: Real-time feedback that query is being processed
2. **⏱️ Performance Timing**: Shows KQL generation and execution times
3. **🔍 Step 1: Context Retrieval**: 
   - Number of relevant fields found
   - Tables identified
   - Similar query patterns retrieved
4. **📋 Context Details**: 
   - Primary tables identified
   - Field analysis results
   - Pattern matching results
5. **🔄 Step 2: Context Processing**: 
   - Prioritization and refinement process
6. **🤖 Step 3: KQL Generation**: 
   - Enhanced context sent to GPT-4
   - Schema-aware generation
7. **✅ Step 4: Validation**: 
   - Query complexity analysis
   - Performance impact assessment
   - Validation warnings
8. **🎯 Step 5: Final Result**: 
   - Validated KQL query
   - Ready for execution

#### **Fallback Mode Indication**
- **⚠️ Fallback Mode**: Clear indication when basic generation is used
- **Initialization Guidance**: Instructions to enable full RAG workflow

#### **Query Results**
- **📊 Results Summary**: Row and column counts
- **🚀 Execution Timing**: Shows Log Analytics query execution time
- **📋 Data Tables**: Interactive dataframes with results

#### **Starting the Enhanced UI**

```bash
# Start the API server first
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, start the Chainlit app
chainlit run chainlit_app/chainlit_app.py --port 8001
```

#### **Example User Experience**

1. **User opens app**: Sees welcome message with RAG status
2. **User types**: "Show me failed login attempts in the last week"
3. **App shows**: 5-step RAG workflow with timing and context details
4. **App displays**: Generated KQL with validation status
5. **App executes**: Query and shows results with performance metrics

This enhanced UI makes the Multi-RAG workflow transparent and educational, helping users understand how their queries are processed and why certain KQL is generated.

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    Multi-RAG Workflow                           │
├─────────────────────────────────────────────────────────────────┤
│  1. Natural Language Query Input                               │
│  2. Vector Similarity Search (Fields, Values, Schemas, Examples)│
│  3. Context Refinement & Prioritization                        │
│  4. Enhanced KQL Generation with Context                       │
│  5. KQL Validation & Correction                                │
│  6. Complexity Analysis & Response                             │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vector Store  │    │ Schema Generator│    │ Schema Refiner  │
│                 │    │                 │    │                 │
│ • Field Desc.   │    │ • Table Discovery│   │ • Context Rank  │
│ • Field Values  │    │ • AI Descriptions│   │ • Pattern Extract│
│ • Schemas       │    │ • Sample Values │    │ • Instruction Gen│
│ • Ground Truth  │    │ • Schema Extract│    │ • Relevance Score│
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🧪 Testing

### Unit Tests
```bash
pytest tests/
```

### Manual Testing
```bash
# Test vector store
python -c "from app.vector_store import VectorStore; vs = VectorStore(); print('✅ Vector store working')"

# Test multi-RAG workflow
python -c "from app.multi_rag_workflow import multi_rag_workflow; print('Status:', multi_rag_workflow.get_workflow_status())"
```

## 🔍 Troubleshooting

### SSL Certificate Issues
If you encounter SSL certificate errors:

1. Run the SSL fix script:
   ```bash
   python scripts/fix_ssl_and_download_model.py
   ```

2. Set environment variables manually:
   ```bash
   export CURL_CA_BUNDLE=$(python -c "import certifi; print(certifi.where())")
   export REQUESTS_CA_BUNDLE=$(python -c "import certifi; print(certifi.where())")
   ```

3. The system will automatically fall back to MockEmbedder if sentence transformers fail

### Common Issues

- **Model Download Fails**: System uses MockEmbedder fallback automatically
- **ChromaDB Errors**: Check write permissions in project directory
- **Azure API Errors**: Verify Azure OpenAI credentials and endpoint
- **Workspace Access**: Ensure proper Azure authentication for Log Analytics

## 📈 Performance Considerations

### RAG Workflow Performance
- **Initialization**: 5-20 minutes depending on workspace size
- **Query Generation**: 2-5 seconds with RAG, <1 second without
- **Vector Search**: Sub-second for similarity searches
- **Memory Usage**: ~500MB-2GB depending on workspace size

### Optimization Tips
- Initialize RAG workflow during off-peak hours
- Use `force_refresh=false` to avoid re-processing existing data
- Limit table processing to most relevant tables for faster initialization
- Monitor vector store size and clean up periodically

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

[Add your license information here]

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs for detailed error messages
3. Open an issue with detailed reproduction steps

---

**Note**: This system includes fallback mechanisms to ensure functionality even when some components (like sentence transformers) fail to load due to network or SSL issues. The MockEmbedder provides basic functionality for testing and development. 