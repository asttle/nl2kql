import chainlit as cl
import requests
import os
import pandas as pd
import json
import time

API_URL = os.getenv("NL2KQL_API_URL", "http://localhost:8000")

import openlit

openlit.init(otlp_endpoint="http://localhost:4318")

@cl.on_chat_start
async def start():
    """Welcome message and RAG workflow status check"""
    # Check RAG workflow status
    try:
        status_response = requests.get(f"{API_URL}/rag-status")
        if status_response.status_code == 200:
            status_data = status_response.json()
            is_initialized = status_data.get("initialized", False)
            total_entries = status_data.get("total_entries", 0)
            
            if is_initialized and total_entries > 0:
                welcome_msg = f"""🎉 **Welcome to NL2KQL with Multi-RAG Workflow!**

✅ **RAG Workflow Status**: Initialized and Ready
📊 **Knowledge Base**: {total_entries} entries loaded
🚀 **Enhanced Features**: Schema-aware generation, validation, and context retrieval

Simply type your natural language query and watch the Multi-RAG workflow in action!

**Example queries:**
• "Show me failed login attempts in the last week"
• "Find processes with high CPU usage"
• "List recent Azure activity logs"
"""
            else:
                welcome_msg = """🎉 **Welcome to NL2KQL with Multi-RAG Workflow!**

⚠️ **RAG Workflow Status**: Not Initialized
📝 **Current Mode**: Basic generation available

To enable the full Multi-RAG workflow with enhanced accuracy:
1. Initialize the workflow with your workspace ID
2. Call the `/initialize-rag` endpoint via API

**You can still use the system now with basic generation!**

**Example queries:**
• "Show me failed login attempts in the last week"
• "Find processes with high CPU usage"
• "List recent Azure activity logs"
"""
        else:
            welcome_msg = """🎉 **Welcome to NL2KQL!**

Ready to convert your natural language queries to KQL!
Type your query below to get started.
"""
    except Exception as e:
        welcome_msg = """🎉 **Welcome to NL2KQL!**

Ready to convert your natural language queries to KQL!
Type your query below to get started.
"""
    
    await cl.Message(content=welcome_msg, author="NL2KQL Bot").send()

@cl.on_message
async def main(message: cl.Message):
    nl = message.content
    start_time = time.time()
    
    # Show initial processing message
    processing_msg = cl.Message(
        content="🔄 Processing your query with Multi-RAG workflow...",
        author="NL2KQL Bot"
    )
    await processing_msg.send()
    
    try:
        # First, call the detailed endpoint to get RAG information
        detailed_start = time.time()
        detailed_response = requests.post(
            f"{API_URL}/nl2kql/detailed", 
            json={
                "natural_language": nl,
                "use_rag": True
            }
        )
        detailed_time = time.time() - detailed_start
        
        if detailed_response.status_code == 200:
            detailed_data = detailed_response.json()
            
            # Show timing for KQL generation
            timing_msg = f"⏱️ **KQL Generation completed in {detailed_time:.2f} seconds**"
            await cl.Message(content=timing_msg, author="Performance").send()
            
            # Show RAG workflow steps if used
            if detailed_data.get("rag_workflow_used", False):
                await show_rag_steps(detailed_data)
            else:
                # Show fallback mode information
                await show_fallback_mode(detailed_data)
            
            # Get the KQL query
            kql = detailed_data.get("kql_query", "")
            
            # Show KQL generation result
            await show_kql_result(detailed_data, kql)
            
            # Now execute the query if it's valid
            if detailed_data.get("is_valid", False) and kql.strip():
                await execute_and_show_results(nl, kql)
            else:
                await cl.Message(
                    content="⚠️ Generated KQL has validation issues. Execution skipped for safety.",
                    author="NL2KQL Bot"
                ).send()
                
            # Show total time
            total_time = time.time() - start_time
            final_timing = f"🏁 **Total processing time: {total_time:.2f} seconds**"
            await cl.Message(content=final_timing, author="Performance").send()
            
        else:
            await cl.Message(
                content=f"❌ Error getting detailed response: {detailed_response.text}",
                author="NL2KQL Bot"
            ).send()
            
    except Exception as e:
        await cl.Message(
            content=f"❌ Error processing query: {str(e)}",
            author="NL2KQL Bot"
        ).send()

async def show_rag_steps(detailed_data):
    """Show the RAG workflow steps and context used"""
    context_used = detailed_data.get("context_used", {})
    
    # Step 1: Context Retrieval
    retrieval_info = f"""🔍 **Step 1: Context Retrieval**
• Found {context_used.get('fields_considered', 0)} relevant fields
• Discovered {context_used.get('tables_considered', 0)} relevant tables
• Retrieved {context_used.get('similar_queries_found', 0)} similar query patterns
• Context: {context_used.get('context_summary', 'No summary available')}"""
    
    await cl.Message(content=retrieval_info, author="RAG Workflow").send()
    
    # Step 1.5: Show what was actually retrieved (if available)
    if context_used.get('tables_considered', 0) > 0:
        context_details = f"""📋 **Context Details**
• **Primary Tables Identified**: Based on your query, the system identified {context_used.get('tables_considered', 0)} relevant table(s)
• **Field Analysis**: {context_used.get('fields_considered', 0)} fields were analyzed for relevance
• **Pattern Matching**: {context_used.get('similar_queries_found', 0)} similar queries found in knowledge base
• **Schema Context**: {context_used.get('context_summary', 'Schema information retrieved')}"""
        
        await cl.Message(content=context_details, author="RAG Workflow").send()
    
    # Step 2: Processing & Refinement
    processing_info = """🔄 **Step 2: Context Processing & Refinement**
• Prioritizing most relevant tables and fields
• Filtering sample values based on query intent
• Extracting patterns from similar successful queries
• Building enhanced context for LLM generation"""
    
    await cl.Message(content=processing_info, author="RAG Workflow").send()
    
    # Step 3: Generation with Context
    generation_info = """🤖 **Step 3: KQL Generation with Enhanced Context**
• Sending refined context to Azure OpenAI GPT-4
• Using specialized KQL generation prompts
• Ensuring field names match actual schema
• Applying learned patterns from similar queries"""
    
    await cl.Message(content=generation_info, author="RAG Workflow").send()
    
    # Step 4: Validation & Quality
    complexity = detailed_data.get("complexity_analysis", {})
    warnings = detailed_data.get("warnings", [])
    
    quality_info = f"""✅ **Step 4: Validation & Quality Analysis**
• Query Complexity: {complexity.get('complexity_score', 'Unknown')}/10
• Performance Impact: {complexity.get('performance_impact', 'Unknown')}
• Time Filter Present: {'Yes' if complexity.get('has_time_filter', False) else 'No'}
• Validation Warnings: {len(warnings)} found"""
    
    if warnings:
        quality_info += f"\n• Warning Details: {'; '.join(warnings[:3])}"
    
    await cl.Message(content=quality_info, author="RAG Workflow").send()
    
    # Step 5: Final Result
    result_info = """🎯 **Step 5: Final Result**
• KQL query validated and corrected if needed
• Complexity analysis completed
• Ready for execution against Log Analytics workspace"""
    
    await cl.Message(content=result_info, author="RAG Workflow").send()

async def show_kql_result(detailed_data, kql):
    """Show the generated KQL with quality indicators"""
    is_valid = detailed_data.get("is_valid", False)
    original_kql = detailed_data.get("original_kql")
    
    status_emoji = "✅" if is_valid else "⚠️"
    status_text = "Valid" if is_valid else "Has Issues"
    
    kql_content = f"""{status_emoji} **Generated KQL Query ({status_text})**
```kusto
{kql}
```"""
    
    # Show if query was corrected
    if original_kql and original_kql != kql:
        kql_content += f"\n🔧 *Query was automatically corrected from original version*"
    
    # Add complexity info
    complexity = detailed_data.get("complexity_analysis", {})
    if complexity:
        operations = complexity.get("operations", {})
        op_summary = []
        for op_type, count in operations.items():
            if count > 0:
                op_summary.append(f"{count} {op_type}")
        
        if op_summary:
            kql_content += f"\n📊 *Operations: {', '.join(op_summary)}*"
    
    await cl.Message(content=kql_content, author="NL2KQL Bot").send()

async def execute_and_show_results(nl, kql):
    """Execute the KQL query and show results"""
    execution_msg = cl.Message(
        content="🚀 Executing query against Log Analytics...",
        author="NL2KQL Bot"
    )
    await execution_msg.send()
    
    # Call the execute endpoint
    execution_start = time.time()
    response = requests.post(f"{API_URL}/execute", json={"natural_language": nl})
    execution_time = time.time() - execution_start
    
    # Show execution timing
    exec_timing_msg = f"⏱️ **Query execution completed in {execution_time:.2f} seconds**"
    await cl.Message(content=exec_timing_msg, author="Performance").send()
    
    if response.status_code == 200:
        data = response.json()
        result = data.get("data", [])
        
        if not result:
            await cl.Message(
                content="📭 Query executed successfully but returned no data.",
                author="NL2KQL Bot"
            ).send()
            return
        
        # Show results for each table
        for table in result:
            if not table["columns"]:
                await cl.Message(
                    content=f"**Table: {table['name']}** - No columns returned.",
                    author="NL2KQL Bot"
                ).send()
                continue
            
            df = pd.DataFrame(table["rows"], columns=table["columns"])
            
            # Create summary
            summary = f"""📊 **Results from {table['name']}**
• Rows returned: {len(df)}
• Columns: {len(df.columns)}"""
            
            await cl.Message(
                content=summary,
                author="NL2KQL Bot",
                elements=[cl.Dataframe(name=table["name"], dataframe=df)]
            ).send()
    else:
        await cl.Message(
            content=f"❌ Execution failed: {response.text}",
            author="NL2KQL Bot"
        ).send()

async def show_fallback_mode(detailed_data):
    """Show information when fallback mode is used instead of RAG workflow"""
    context_used = detailed_data.get("context_used", {})
    context_summary = context_used.get("context_summary", "")
    
    if "Fallback generation used" in context_summary:
        fallback_info = """⚠️ **Fallback Mode Active**
• Multi-RAG workflow not available or failed
• Using basic Azure OpenAI generation
• Limited context awareness
• Consider initializing RAG workflow for better results"""
    else:
        fallback_info = """📝 **Basic Generation Mode**
• Multi-RAG workflow not used for this query
• Using standard KQL generation
• Limited schema context available"""
    
    await cl.Message(content=fallback_info, author="NL2KQL Bot").send()
    
    # Show what context was available
    if context_summary and context_summary != "Fallback generation used":
        context_info = f"""📋 **Available Context**
• {context_summary}"""
        await cl.Message(content=context_info, author="NL2KQL Bot").send()