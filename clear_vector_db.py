#!/usr/bin/env python3
"""Clear all data from the ChromaDB vector database."""

import os
import shutil
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def clear_chromadb(persist_directory: str = "./chroma_db"):
    """Clear all ChromaDB data by removing the persistence directory."""
    db_path = Path(persist_directory)
    
    if db_path.exists():
        try:
            shutil.rmtree(db_path)
            logger.info(f"✅ Cleared ChromaDB data from {persist_directory}")
            logger.info("Vector database is now empty and ready for your documents")
        except Exception as e:
            logger.error(f"❌ Failed to clear ChromaDB data: {e}")
    else:
        logger.info(f"✅ ChromaDB directory {persist_directory} doesn't exist - already clean")

def main():
    """Main function to clear the vector database."""
    print("🧹 Clearing Japan Helpdesk Vector Database")
    print("=" * 50)
    
    # Clear the default ChromaDB directory
    clear_chromadb()
    
    print("\n📋 Next Steps:")
    print("1. Start the server: uv run uvicorn app.server:app --reload")
    print("2. Add your documents: uv run python ingest_documents.py /path/to/your/docs")
    print("3. Test queries with empty database to see fallback behavior")
    print("\n🎯 Your system is now ready for real testing!")

if __name__ == "__main__":
    main()
