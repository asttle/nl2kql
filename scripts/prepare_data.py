#!/usr/bin/env python3
"""
Data Preparation Script for NL2KQL Multi-RAG Workflow

This script helps initialize the multi-RAG workflow by:
1. Discovering tables in your Log Analytics workspace
2. Extracting schema information
3. Generating AI-powered field descriptions
4. Populating vector stores for similarity search

Usage:
    python scripts/prepare_data.py --workspace-id <your-workspace-id>
"""

import sys
import os
import asyncio
import argparse
import logging
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.multi_rag_workflow import multi_rag_workflow
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('data_preparation.log')
    ]
)

logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(description='Prepare data for NL2KQL Multi-RAG Workflow')
    parser.add_argument('--workspace-id', required=True, help='Azure Log Analytics Workspace ID')
    parser.add_argument('--force-refresh', action='store_true', help='Force refresh of existing data')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done without actually doing it')
    
    args = parser.parse_args()
    
    logger.info("Starting NL2KQL Multi-RAG Workflow Data Preparation")
    logger.info(f"Workspace ID: {args.workspace_id}")
    logger.info(f"Force Refresh: {args.force_refresh}")
    logger.info(f"Dry Run: {args.dry_run}")
    
    # Validate configuration
    if not settings.azure_openai_endpoint or not settings.azure_openai_key:
        logger.error("Azure OpenAI configuration is missing. Please check your .env file.")
        sys.exit(1)
    
    try:
        if args.dry_run:
            logger.info("DRY RUN MODE - No actual changes will be made")
            
            # Show current status
            status = multi_rag_workflow.get_workflow_status()
            logger.info(f"Current RAG workflow status: {status}")
            
            # Discover tables (without processing)
            tables = multi_rag_workflow.schema_generator.discover_tables(args.workspace_id)
            logger.info(f"Would process {len(tables)} tables: {tables[:10]}...")
            
            logger.info("Dry run completed. Use --force-refresh to actually initialize the workflow.")
        else:
            # Initialize the workflow
            logger.info("Initializing Multi-RAG Workflow...")
            await multi_rag_workflow.initialize_workflow(args.workspace_id, args.force_refresh)
            
            # Show final status
            status = multi_rag_workflow.get_workflow_status()
            logger.info("Data preparation completed successfully!")
            logger.info(f"Final status: {status}")
            
            # Show some statistics
            stats = status['vector_store_stats']
            logger.info(f"Vector store populated with:")
            logger.info(f"  - {stats['field_descriptions']} field descriptions")
            logger.info(f"  - {stats['field_values']} field value sets")
            logger.info(f"  - {stats['schemas']} table schemas")
            logger.info(f"  - {stats['ground_truth_pairs']} ground truth examples")
            
            logger.info("The Multi-RAG workflow is now ready to use!")
            
    except Exception as e:
        logger.error(f"Data preparation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 