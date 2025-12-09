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
    """Converts a list of Document objects into a single formatted string, including metadata."""
    formatted_parts = []
    for doc in docs:
        source = doc.metadata.get('source', 'unknown')
        
        # Check if this is a Facebook post with engagement metrics
        if doc.metadata.get('engagement_type') == 'facebook_post':
            likes = doc.metadata.get('likes_count', 'unknown')
            shares = doc.metadata.get('shares_count', 'unknown')
            comments = doc.metadata.get('comments_count', 'unknown')
            reactions = doc.metadata.get('reactions_count', 'unknown')
            
            formatted_part = f"Source: {source}\nContent: {doc.page_content}\nEngagement Metrics: Likes: {likes}, Shares: {shares}, Comments: {comments}, Reactions: {reactions}"
        else:
            formatted_part = f"Source: {source}\nContent: {doc.page_content}"
        
        formatted_parts.append(formatted_part)
    
    return "\n\n".join(formatted_parts)

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
    For Facebook and TikTok data, also stores engagement metrics in metadata.
    """
    if not data_list:
        print(f"No data found for {source}. Skipping.")
        return 0

    print(f"Preparing {len(data_list)} {source} entries for ChromaDB...")

    documents_to_add: List[Document] = [] 
    ids_batch: List[str] = []
    
    for i, entry in enumerate(data_list):
        if isinstance(entry, dict):
            text = entry.get("text") or entry.get("post_text") or entry.get("title") or entry.get("description")
        else:
            text = str(entry)
        
        if text and text != "Error scraping post details":
            # Prepare metadata based on source
            metadata = {"source": source, "type": "post"}
            
            # Facebook-specific engagement metrics to metadata
            if source == "facebook":
                likes = entry.get("likes")
                shares = entry.get("shares") 
                comments = entry.get("comments")
                reactions = entry.get("topReactionsCount")
                
                print(f"  Facebook post {i}: likes={likes}, shares={shares}, comments={comments}, reactions={reactions}")
                
                metadata.update({
                    "post_id": entry.get("postId", f"{source}_{i}"),
                    "facebook_url": entry.get("url"),
                    "post_time": entry.get("time"),
                    "likes_count": likes,
                    "shares_count": shares,
                    "comments_count": comments if isinstance(comments, int) else 0,
                    "reactions_count": reactions,
                    "engagement_type": "facebook_post"
                })
            # TikTok-specific engagement metrics to metadata
            elif source == "tiktok":
                digg_count = entry.get("diggCount")
                share_count = entry.get("shareCount")
                play_count = entry.get("playCount")
                comment_count = entry.get("commentCount")
                
                print(f"  TikTok post {i}: likes={digg_count}, shares={share_count}, plays={play_count}, comments={comment_count}")

                metadata.update({
                    "post_id": entry.get("id", f"{source}_{i}"), # TikTok uses 'id' field
                    "tiktok_url": entry.get("webVideoUrl"), # TikTok uses 'webVideoUrl' field
                    "post_time": entry.get("createTimeISO"), # Use ISO format if available, or 'createTime'
                    "likes_count": digg_count, # TikTok calls likes "digs" or "hearts"
                    "shares_count": share_count,
                    "comments_count": comment_count,
                    "plays_count": play_count, # View count
                    "engagement_type": "tiktok_post"
                })
            else:
                # Default for website, linkedin, etc.
                metadata["post_id"] = entry.get("postId", f"{source}_{i}")
        
            # Create document with engagement metrics in metadata
            doc = Document(
                page_content=text,
                metadata=metadata
            )
            documents_to_add.append(doc)
            ids_batch.append(f"{source}_post_{i}")

    if documents_to_add:
        print(f"Ingesting {len(documents_to_add)} documents ({source}) into ChromaDB...")
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
    Gets relevant documents, removes duplicates based on content, and formats them into a single string.
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
    
    # Deduplication logic
    seen_contents = set()
    unique_docs = []
    for doc in docs:
        content_key = doc.page_content.strip().lower() 
        if content_key not in seen_contents:
            seen_contents.add(content_key)
            unique_docs.append(doc)
        else:
            print(f"  - Deduplicated document with content: {doc.page_content[:50]}...")
    
    if not unique_docs:
        print("All retrieved documents were duplicates.")
        
    return format_docs(unique_docs) 

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

    facebook_json_path = os.path.join(DATA_DIR, "facebook_data.json")
    print(f"Loading facebook data from: {facebook_json_path}")
    facebook_json = load_json_data(facebook_json_path)

    tiktok_json_path = os.path.join(DATA_DIR, "tiktok_data.json")
    print(f"Loading tiktok data from: {tiktok_json_path}")
    tiktok_json = load_json_data(tiktok_json_path)

    website_data = website_json.get("data", []) if isinstance(website_json, dict) else website_json
    linkedin_data = linkedin_json.get("data", []) if isinstance(linkedin_json, dict) else linkedin_json
    facebook_data = facebook_json.get("data", []) if isinstance(facebook_json, dict) else facebook_json
    tiktok_data = tiktok_json.get("data", []) if isinstance(tiktok_json, dict) else tiktok_json

    total_added = 0
    total_added += ingest_data(website_data, "website")
    total_added += ingest_data(linkedin_data, "linkedin")
    total_added += ingest_data(facebook_data, "facebook")
    total_added += ingest_data(tiktok_data, "tiktok")

    try:
        count_result = vector_store._collection.count()
        print(f"\n--- Ingestion Complete ---")
        print(f"Total items in ChromaDB: {count_result}")
        return count_result
    except Exception as e:
        print(f"Error counting items in collection: {e}")
        return total_added

def run_clear_chroma():
    """
    Deletes all data from the 'enterprise_data' collection.
    """
    print("--- Chroma Service: Clearing 'enterprise_data' collection ---")
    try:
        temp_vector_store = Chroma(
            collection_name="enterprise_data",
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        temp_vector_store.delete_collection()
        print("Collection deleted.")
        
        global vector_store, retriever
        vector_store = Chroma(
            collection_name="enterprise_data",
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 5} 
        )
        
        print("Collection re-created with new instance.")
        return "Collection 'enterprise_data' cleared and re-created successfully."
    except Exception as e:
        print(f"Error clearing collection: {e}")
        raise e            

print("ChromaDB Service file loaded.")