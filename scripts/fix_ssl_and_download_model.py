#!/usr/bin/env python3
"""
Script to fix SSL issues and download the sentence transformer model

This script attempts to:
1. Fix SSL certificate issues
2. Download the sentence transformer model
3. Test the model loading
"""

import os
import ssl
import certifi
import sys
from pathlib import Path

def fix_ssl_certificates():
    """Fix SSL certificate issues"""
    print("Setting up SSL certificates...")
    
    # Set environment variables
    cert_path = certifi.where()
    os.environ['CURL_CA_BUNDLE'] = cert_path
    os.environ['REQUESTS_CA_BUNDLE'] = cert_path
    os.environ['SSL_CERT_FILE'] = cert_path
    
    print(f"SSL certificates set to: {cert_path}")
    
    # Create SSL context
    ssl_context = ssl.create_default_context(cafile=cert_path)
    ssl._create_default_https_context = lambda: ssl_context
    
    return True

def download_model():
    """Download the sentence transformer model"""
    try:
        print("Attempting to download sentence transformer model...")
        
        # Try different approaches
        approaches = [
            lambda: download_with_huggingface_hub(),
            lambda: download_with_sentence_transformers(),
            lambda: download_with_offline_mode()
        ]
        
        for i, approach in enumerate(approaches, 1):
            try:
                print(f"Approach {i}: {approach.__name__}")
                result = approach()
                if result:
                    print(f"Success with approach {i}")
                    return True
            except Exception as e:
                print(f"Approach {i} failed: {e}")
                continue
        
        print("All download approaches failed")
        return False
        
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

def download_with_huggingface_hub():
    """Try downloading with huggingface_hub"""
    from huggingface_hub import snapshot_download
    
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    cache_dir = Path.home() / ".cache" / "huggingface" / "transformers"
    
    print(f"Downloading {model_name} to {cache_dir}")
    snapshot_download(repo_id=model_name, cache_dir=cache_dir)
    return True

def download_with_sentence_transformers():
    """Try downloading with sentence_transformers directly"""
    from sentence_transformers import SentenceTransformer
    
    print("Loading sentence transformer model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Test the model
    test_text = "This is a test sentence."
    embedding = model.encode([test_text])
    print(f"Model loaded successfully. Test embedding shape: {embedding.shape}")
    return True

def download_with_offline_mode():
    """Try using offline mode if model exists"""
    from sentence_transformers import SentenceTransformer
    
    print("Attempting to load model in offline mode...")
    model = SentenceTransformer('all-MiniLM-L6-v2', local_files_only=True)
    return True

def test_vector_store():
    """Test if the vector store can be imported and used"""
    try:
        print("Testing vector store import...")
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from app.vector_store import VectorStore
        
        print("Creating vector store instance...")
        vs = VectorStore()
        
        print("Testing embedding generation...")
        # This should work with either real model or MockEmbedder
        test_docs = ["test document 1", "test document 2"]
        embeddings = vs.embedder.encode(test_docs)
        print(f"Embeddings generated successfully. Shape: {embeddings.shape}")
        
        return True
        
    except Exception as e:
        print(f"Vector store test failed: {e}")
        return False

def main():
    print("=== SSL Fix and Model Download Script ===")
    
    # Step 1: Fix SSL
    print("\n1. Fixing SSL certificates...")
    ssl_fixed = fix_ssl_certificates()
    
    if not ssl_fixed:
        print("Failed to fix SSL certificates")
        return False
    
    # Step 2: Try to download model
    print("\n2. Downloading sentence transformer model...")
    model_downloaded = download_model()
    
    if not model_downloaded:
        print("Model download failed, but MockEmbedder fallback will be used")
    
    # Step 3: Test vector store
    print("\n3. Testing vector store...")
    vs_working = test_vector_store()
    
    if vs_working:
        print("\n✅ Vector store is working!")
    else:
        print("\n❌ Vector store test failed")
        return False
    
    print("\n=== Setup Complete ===")
    print("The NL2KQL system is ready to use!")
    print("- If the real model downloaded: Full embedding functionality")
    print("- If using MockEmbedder: Basic functionality for testing")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 