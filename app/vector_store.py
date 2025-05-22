import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import json
import logging
from pathlib import Path
import ssl
import certifi
import os

logger = logging.getLogger(__name__)

class VectorStore:
    """Vector store for managing embeddings and similarity search in the multi-RAG workflow"""
    
    def __init__(self, persist_directory: str = "./chroma_db"):
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(exist_ok=True)
        
        # Initialize ChromaDB with persistence
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Initialize sentence transformer for embeddings with SSL fix
        self.embedder = self._initialize_embedder()
        
        # Initialize collections for different types of data
        self.field_descriptions_collection = self._get_or_create_collection("field_descriptions")
        self.field_values_collection = self._get_or_create_collection("field_values")
        self.schemas_collection = self._get_or_create_collection("schemas")
        self.ground_truth_collection = self._get_or_create_collection("ground_truth_pairs")
        
        logger.info(f"VectorStore initialized with persist directory: {self.persist_directory}")
    
    def _initialize_embedder(self):
        """Initialize sentence transformer with SSL handling"""
        try:
            # Set SSL context to use certifi certificates
            ssl_context = ssl.create_default_context(cafile=certifi.where())
            
            # Set environment variables for SSL
            os.environ['CURL_CA_BUNDLE'] = certifi.where()
            os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
            
            logger.info("Initializing sentence transformer model...")
            embedder = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Sentence transformer model loaded successfully")
            return embedder
            
        except Exception as e:
            logger.warning(f"Failed to load sentence transformer model: {e}")
            logger.info("Attempting to use a simpler embedding approach...")
            
            try:
                # Try with trust_remote_code=False and local_files_only if model exists
                embedder = SentenceTransformer('all-MiniLM-L6-v2', trust_remote_code=False)
                return embedder
            except Exception as e2:
                logger.error(f"Failed to load any sentence transformer model: {e2}")
                # Return a mock embedder for testing
                return MockEmbedder()
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection"""
        try:
            return self.client.get_collection(name)
        except Exception:  # Changed from ValueError to Exception to catch all errors
            return self.client.create_collection(name)
    
    def add_field_descriptions(self, field_descriptions: List[Dict[str, Any]]):
        """Add field descriptions to the vector store
        
        Args:
            field_descriptions: List of dicts with keys: table_name, field_name, description, data_type
        """
        documents = []
        metadatas = []
        ids = []
        
        for i, field_desc in enumerate(field_descriptions):
            # Create a rich description for embedding
            doc_text = f"Table: {field_desc['table_name']}, Field: {field_desc['field_name']}, Type: {field_desc['data_type']}, Description: {field_desc['description']}"
            documents.append(doc_text)
            
            metadatas.append({
                "table_name": field_desc['table_name'],
                "field_name": field_desc['field_name'],
                "data_type": field_desc['data_type'],
                "description": field_desc['description']
            })
            
            ids.append(f"field_{field_desc['table_name']}_{field_desc['field_name']}_{i}")
        
        # Generate embeddings
        embeddings = self.embedder.encode(documents).tolist()
        
        self.field_descriptions_collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Added {len(field_descriptions)} field descriptions to vector store")
    
    def add_field_values(self, field_values: List[Dict[str, Any]]):
        """Add field values to the vector store
        
        Args:
            field_values: List of dicts with keys: table_name, field_name, sample_values
        """
        documents = []
        metadatas = []
        ids = []
        
        for i, field_val in enumerate(field_values):
            # Create a document with sample values
            sample_values_str = ", ".join(str(v) for v in field_val['sample_values'][:10])  # Limit to 10 samples
            doc_text = f"Table: {field_val['table_name']}, Field: {field_val['field_name']}, Sample values: {sample_values_str}"
            documents.append(doc_text)
            
            metadatas.append({
                "table_name": field_val['table_name'],
                "field_name": field_val['field_name'],
                "sample_values": json.dumps(field_val['sample_values'][:20])  # Store up to 20 samples
            })
            
            ids.append(f"values_{field_val['table_name']}_{field_val['field_name']}_{i}")
        
        # Generate embeddings
        embeddings = self.embedder.encode(documents).tolist()
        
        self.field_values_collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Added {len(field_values)} field value sets to vector store")
    
    def add_schemas(self, schemas: List[Dict[str, Any]]):
        """Add table schemas to the vector store
        
        Args:
            schemas: List of dicts with keys: table_name, schema, description
        """
        documents = []
        metadatas = []
        ids = []
        
        for i, schema in enumerate(schemas):
            # Create a document with schema information
            doc_text = f"Table: {schema['table_name']}, Description: {schema['description']}, Schema: {schema['schema']}"
            documents.append(doc_text)
            
            metadatas.append({
                "table_name": schema['table_name'],
                "schema": schema['schema'],
                "description": schema['description']
            })
            
            ids.append(f"schema_{schema['table_name']}_{i}")
        
        # Generate embeddings
        embeddings = self.embedder.encode(documents).tolist()
        
        self.schemas_collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Added {len(schemas)} schemas to vector store")
    
    def add_ground_truth_pairs(self, pairs: List[Dict[str, Any]]):
        """Add ground truth NL2KQL pairs to the vector store
        
        Args:
            pairs: List of dicts with keys: natural_language, kql_query, description
        """
        documents = []
        metadatas = []
        ids = []
        
        for i, pair in enumerate(pairs):
            # Use natural language as the document for similarity search
            documents.append(pair['natural_language'])
            
            metadatas.append({
                "natural_language": pair['natural_language'],
                "kql_query": pair['kql_query'],
                "description": pair.get('description', '')
            })
            
            ids.append(f"ground_truth_{i}")
        
        # Generate embeddings
        embeddings = self.embedder.encode(documents).tolist()
        
        self.ground_truth_collection.add(
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            ids=ids
        )
        
        logger.info(f"Added {len(pairs)} ground truth pairs to vector store")
    
    def search_relevant_fields(self, query: str, n_results: int = 10) -> List[Dict[str, Any]]:
        """Search for relevant field descriptions based on the query"""
        query_embedding = self.embedder.encode([query]).tolist()
        
        results = self.field_descriptions_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        relevant_fields = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata in results['metadatas'][0]:
                relevant_fields.append(metadata)
        
        return relevant_fields
    
    def search_relevant_values(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for relevant field values based on the query"""
        query_embedding = self.embedder.encode([query]).tolist()
        
        results = self.field_values_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        relevant_values = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata in results['metadatas'][0]:
                # Parse sample values back from JSON
                metadata['sample_values'] = json.loads(metadata['sample_values'])
                relevant_values.append(metadata)
        
        return relevant_values
    
    def search_relevant_schemas(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        """Search for relevant schemas based on the query"""
        query_embedding = self.embedder.encode([query]).tolist()
        
        results = self.schemas_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        relevant_schemas = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata in results['metadatas'][0]:
                relevant_schemas.append(metadata)
        
        return relevant_schemas
    
    def search_similar_queries(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search for similar ground truth queries"""
        query_embedding = self.embedder.encode([query]).tolist()
        
        results = self.ground_truth_collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        similar_queries = []
        if results['metadatas'] and results['metadatas'][0]:
            for metadata in results['metadatas'][0]:
                similar_queries.append(metadata)
        
        return similar_queries
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about the collections"""
        return {
            "field_descriptions": self.field_descriptions_collection.count(),
            "field_values": self.field_values_collection.count(),
            "schemas": self.schemas_collection.count(),
            "ground_truth_pairs": self.ground_truth_collection.count()
        } 

class MockEmbedder:
    """Mock embedder for testing when sentence transformer fails to load"""
    
    def __init__(self):
        self.embedding_dim = 384  # Same as all-MiniLM-L6-v2
        logger.warning("Using MockEmbedder - embeddings will be random vectors for testing only")
    
    def encode(self, texts):
        """Generate random embeddings for testing"""
        import numpy as np
        if isinstance(texts, str):
            texts = [texts]
        
        # Generate random embeddings with consistent seed for reproducibility
        np.random.seed(hash(' '.join(texts)) % 2**32)
        embeddings = np.random.normal(0, 1, (len(texts), self.embedding_dim))
        
        # Normalize embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        embeddings = embeddings / norms
        
        return embeddings 