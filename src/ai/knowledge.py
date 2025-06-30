import os
import asyncio
from pathlib import Path
from typing import List
import chromadb
from chromadb.config import Settings
from langchain_text_splitters import RecursiveCharacterTextSplitter
import PyPDF2
import openai
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_db
from src.bots import crud as bots_crud

# ChromaDB setup
CHROMA_DB_PATH = "db/chroma_db"
KNOWLEDGE_BASES_DIR = Path("temp_knowledge_bases")

# Ensure directories exist
KNOWLEDGE_BASES_DIR.mkdir(exist_ok=True)
Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)

# Initialize ChromaDB client
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def process_and_store_knowledge_base(bot_id: int, file_path: str) -> None:
    """
    Process a PDF file and store it as embeddings in ChromaDB.
    
    Args:
        bot_id: The bot ID this knowledge base belongs to
        file_path: Path to the uploaded PDF file
    """
    try:
        print(f"Starting knowledge base processing for bot {bot_id}")
        
        async for db in get_async_db():
            await bots_crud.update_bot_knowledge_status(db, bot_id, "processing")
            break
        

        print(f"Extracting text from PDF: {file_path}")
        raw_text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                raw_text += page.extract_text() + "\n\n"
        
        if not raw_text.strip():
            raise ValueError("No text could be extracted from the PDF")
        
        # 2. Chunk the text
        print("Chunking text...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len,
        )
        chunks = text_splitter.split_text(raw_text)
        
        if not chunks:
            raise ValueError("No text chunks were created")
        
        print(f"Created {len(chunks)} text chunks")
        
        # 3. Generate embeddings and store in ChromaDB
        collection_name = f"bot_{bot_id}_kb"
        
        # Delete existing collection if it exists
        try:
            chroma_client.delete_collection(name=collection_name)
        except:
            pass  # Collection doesn't exist yet
        
        # Create new collection
        collection = chroma_client.create_collection(
            name=collection_name,
            metadata={"bot_id": bot_id}
        )
        
        # Generate embeddings for all chunks
        print("Generating embeddings...")
        embeddings_response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks
        )
        
        embeddings = [embedding.embedding for embedding in embeddings_response.data]
        
        # Store in ChromaDB
        chunk_ids = [f"chunk_{i}" for i in range(len(chunks))]
        collection.add(
            embeddings=embeddings,
            documents=chunks,
            ids=chunk_ids
        )
        
        print(f"Stored {len(chunks)} chunks in ChromaDB collection '{collection_name}'")
        
        # Update bot status to ready
        async for db in get_async_db():
            await bots_crud.update_bot_knowledge_status(db, bot_id, "ready")
            break
        
        print(f"Knowledge base processing completed for bot {bot_id}")
        
    except Exception as e:
        print(f"Error processing knowledge base for bot {bot_id}: {e}")
        
        # Update bot status to failed
        async for db in get_async_db():
            await bots_crud.update_bot_knowledge_status(db, bot_id, "failed")
            break
        
        raise


def get_knowledge_base_collection(bot_id: int) -> chromadb.Collection:
    """
    Get the ChromaDB collection for a specific bot's knowledge base.
    
    Args:
        bot_id: The bot ID
        
    Returns:
        ChromaDB collection
    """
    collection_name = f"bot_{bot_id}_kb"
    try:
        return chroma_client.get_collection(name=collection_name)
    except Exception as e:
        raise ValueError(f"Knowledge base not found for bot {bot_id}: {e}")


async def query_knowledge_base(bot_id: int, query: str, n_results: int = 4) -> List[str]:
    """
    Query the knowledge base for relevant context.
    
    Args:
        bot_id: The bot ID
        query: The user's question
        n_results: Number of relevant chunks to retrieve
        
    Returns:
        List of relevant text chunks
    """
    try:
        collection = get_knowledge_base_collection(bot_id)
        
        # Generate embedding for the query
        embeddings_response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[query]
        )
        query_embedding = embeddings_response.data[0].embedding
        
        # Query the collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return results['documents'][0] if results['documents'] else []
        
    except Exception as e:
        print(f"Error querying knowledge base for bot {bot_id}: {e}")
        return []


def delete_knowledge_base(bot_id: int) -> None:
    """
    Delete the knowledge base for a specific bot.
    
    Args:
        bot_id: The bot ID
    """
    collection_name = f"bot_{bot_id}_kb"
    try:
        chroma_client.delete_collection(name=collection_name)
        print(f"Deleted knowledge base for bot {bot_id}")
    except Exception as e:
        print(f"Error deleting knowledge base for bot {bot_id}: {e}") 