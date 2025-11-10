import os
import json
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel 
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
import chromadb 

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize ChromaDB connection
print("Connecting to persistent ChromaDB...")
script_dir = os.path.dirname(__file__)
project_root = os.path.join(script_dir, '..', '..', '..')
CHROMA_PERSIST_DIR = os.path.join(project_root, 'chroma_data')
DATA_DIR = os.path.join(project_root, 'data') 

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

# Ingestion logic
def load_json_data(file_path):
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}. File might be empty or corrupt.")
        return []

def ingest_data(data_list, source):
    """
    Converts data list into LangChain Document objects and adds them to the vector store.
    """
    if not data_list:
        print(f"No data found for {source}. Skipping.")
        return 0

    print(f"Preparing {len(data_list)} {source} entries for ChromaDB...")

    documents_to_add: List[Document] = [] 
    ids_batch: List[str] = []
    
    for i, entry in enumerate(data_list):
        if isinstance(entry, dict):
            text = entry.get("post_text") or entry.get("text") or entry.get("title") or entry.get("description")
        else:
            text = str(entry)
        
        if not text or text == "Error scraping post details":
            print(f"Skipping entry {i} from {source} due to missing or error text.")
            continue

        # Creating LangChain Document object
        doc = Document(
            page_content=text,
            metadata={"source": source}
        )
        documents_to_add.append(doc)
        ids_batch.append(f"{source}_{i}")

    if documents_to_add:
        print(f"Ingesting {len(documents_to_add)} documents from {source} into ChromaDB...")
        vector_store.add_documents(
            documents=documents_to_add,
            ids=ids_batch
        )
        print(f"{source} data successfully stored in ChromaDB!")
        return len(documents_to_add)
    else:
        print(f"No valid documents found to ingest for {source}.")
        return 0

# Service functions
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

# Admin service functions
def run_chroma_ingestion() -> int:
    """
    Loads all specified data files and ingests them into ChromaDB.
    """
    print("--- Chroma Service: Running Full Data Ingestion ---")
    
    website_json_path = os.path.join(DATA_DIR, "website_data.json")
    print(f"Loading website data from: {website_json_path}")
    website_json = load_json_data(website_json_path)
    
    linkedin_json_path = os.path.join(DATA_DIR, "linkedin_data.json")
    print(f"Loading linkedin data from: {linkedin_json_path}")
    linkedin_json = load_json_data(linkedin_json_path)
    
    website_data = website_json.get("data", []) if isinstance(website_json, dict) else website_json
    linkedin_data = linkedin_json.get("data", []) if isinstance(linkedin_json, dict) else linkedin_json

    total_added = 0
    total_added += ingest_data(website_data, "website")
    total_added += ingest_data(linkedin_data, "linkedin")

    try:
        total_items = vector_store.collection.count()
        print(f"\n--- Ingestion Complete ---")
        print(f"Total items in ChromaDB: {total_items}")
        return total_items
    except Exception as e:
        print(f"Error counting items in collection: {e}")
        return total_added

def run_clear_chroma():
    """
    Deletes all data from the 'enterprise_data' collection.
    """
    print("--- Chroma Service: Clearing 'enterprise_data' collection ---")
    try:
        vector_store.delete_collection()
        print("Collection deleted.")
        vector_store.collection = vector_store._client.get_or_create_collection(
            name="enterprise_data",
            embedding_function=embeddings
        )
        print("Collection re-created.")
        return "Collection 'enterprise_data' cleared successfully."
    except Exception as e:
        print(f"Error clearing collection: {e}")
        # Try to re create 
        try:
            vector_store.collection = vector_store._client.get_or_create_collection(
                name="enterprise_data",
                embedding_function=embeddings
            )
            print("Collection created.")
            return "Collection created."
        except Exception as e2:
            print(f"Error re-creating collection: {e2}")
            raise e2

print("ChromaDB Service file loaded.")