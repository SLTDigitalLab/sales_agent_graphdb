import os
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel 
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize ChromaDB connection
print("Connecting to persistent ChromaDB...")
script_dir = os.path.dirname(__file__)
project_root = os.path.join(script_dir, '..', '..', '..')
CHROMA_PERSIST_DIR = os.path.join(project_root, 'chroma_data')

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vector_store = Chroma(
    collection_name="enterprise_data",
    embedding_function=embeddings,
    persist_directory=CHROMA_PERSIST_DIR
)

retriever = vector_store.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 5} 
)
print("ChromaDB vector store and retriever initialized for service.")

# Helper function to format retrieved documents
def format_docs(docs: List[Document]) -> str:
    """Converts a list of Document objects into a single formatted string."""
    return "\n\n".join(f"Source: {doc.metadata.get('source', 'unknown')}\nContent: {doc.page_content}" for doc in docs)

# Define the Pydantic Model
class DocumentResult(BaseModel):
    page_content: str
    metadata: Dict[str, Any]

# Define the service function
async def get_raw_chunks(query: str, k: int = 3) -> List[DocumentResult]:
    """
    Executes the synchronous retrieval method in a separate thread.
    """
    print(f"Chroma Service: Received query: {query}")
    if not retriever:
        print("Retriever not available.")
        return []
    
    docs: List[Document] = await asyncio.to_thread(
        retriever.get_relevant_documents, 
        query, 
        k=k
    )

    results = []
    for doc in docs:
        results.append(
            DocumentResult(
                page_content=doc.page_content,
                metadata=doc.metadata
            )
        )
    
    return results

async def get_formatted_chunks(query: str, k: int = 3) -> str:
    """
    Gets relevant documents and formats them into a single string.
    This is what the agent's query_vector_db node will call.
    """
    print(f"Chroma Service: Received formatted query: {query}")
    if not retriever:
        print("Retriever not available.")
        return "Vector store retriever is not initialized."
    
    docs: List[Document] = await asyncio.to_thread(
        retriever.get_relevant_documents,
        query,
        k=k
    )
    
    if not docs:
        return "No relevant information found in the vector database."
        
    return format_docs(docs)

print("ChromaDB Service file loaded.")