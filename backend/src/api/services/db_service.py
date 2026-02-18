import os
import json
import asyncio
from typing import List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel 
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, select, update, delete
from sqlalchemy.orm import sessionmaker, declarative_base
from src.api.schemas import ProductCreate, ProductUpdate
import chromadb 


# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# POSTGRESQL CONFIGURATION 
DATABASE_URL = os.getenv("DATABASE_URL") 
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define the Product Model for SQLAlchemy
class ProductModel(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String)
    description = Column(Text)
    price = Column(Float, default=0.0)
    stock_quantity = Column(Integer, default=0)
    image_url = Column(String)

# --- PRODUCT CRUD FUNCTIONS (SKU-BASED) ---

def get_all_products():
    """Fetch all products from PostgreSQL."""
    with SessionLocal() as session:
        return session.query(ProductModel).all()

def get_product_by_sku(sku: str):
    """Retrieve a single product by its SKU."""
    with SessionLocal() as session:
        return session.query(ProductModel).filter(ProductModel.sku == sku).first()

def create_product(product_data: ProductCreate):
    """Add a new product to PostgreSQL."""
    with SessionLocal() as session:
        db_product = ProductModel(**product_data.dict())
        session.add(db_product)
        session.commit()
        session.refresh(db_product)
        return db_product

def update_product_in_db_by_sku(sku: str, update_data: ProductUpdate):
    """Update product fields in PostgreSQL using the SKU."""
    with SessionLocal() as session:
        db_product = session.query(ProductModel).filter(ProductModel.sku == sku).first()
        if not db_product:
            return None
        
        # Apply only the fields that were provided in the request
        update_dict = update_data.dict(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_product, key, value)
            
        session.commit()
        session.refresh(db_product)
        return db_product

def delete_product_from_db_by_sku(sku: str):
    """Delete a product from PostgreSQL using the SKU."""
    with SessionLocal() as session:
        db_product = session.query(ProductModel).filter(ProductModel.sku == sku).first()
        if db_product:
            session.delete(db_product)
            session.commit()
            return True
        return False

# Initialize ChromaDB connection
logger.info("Connecting to persistent ChromaDB...")
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
logger.info("ChromaDB vector store and retriever initialized for service.")

# TEXT SPLITTER
# Used for ALL data sources to ensure consistent chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)

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
        logger.error(f"File not found: {file_path}")
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.error(f"Error: Could not decode JSON from {file_path}. File might be empty or corrupt.")
        return []

def ingest_data(data_list, source):
    """
    Converts data list into LangChain Document objects, SPLITS THEM, 
    and adds them to the vector store.
    """
    if not data_list:
        logger.warning(f"No data found for {source}. Skipping.")
        return 0

    logger.info(f"Preparing {source} data...")

    documents_to_process: List[Document] = [] 
    
    for i, entry in enumerate(data_list):
        # 1. Extract Text
        if isinstance(entry, dict):
            # Website usually uses 'content', Social uses 'text'/'post_text'
            text = entry.get("content") or entry.get("text") or entry.get("post_text") or entry.get("title") or entry.get("description") or ""
        else:
            text = str(entry)
        
        # 2. Extract Metadata (if text exists)
        if text and text != "Error scraping post details":
            metadata = {"source": source, "type": "post" if source != "website" else "website"}
            
            # Helper to get ID safely
            if source == "website":
                metadata["url"] = entry.get("url", "website_unknown")
            elif source == "facebook":
                likes = entry.get("likes")
                shares = entry.get("shares") 
                comments = entry.get("comments")
                reactions = entry.get("topReactionsCount")
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
            elif source == "tiktok":
                digg_count = entry.get("diggCount")
                share_count = entry.get("shareCount")
                play_count = entry.get("playCount")
                comment_count = entry.get("commentCount")
                metadata.update({
                    "post_id": entry.get("id", f"{source}_{i}"),
                    "tiktok_url": entry.get("webVideoUrl"),
                    "post_time": entry.get("createTimeISO"),
                    "likes_count": digg_count,
                    "shares_count": share_count,
                    "comments_count": comment_count,
                    "plays_count": play_count,
                    "engagement_type": "tiktok_post"
                })
            else:
                # Default (LinkedIn, etc.)
                metadata["post_id"] = entry.get("postId", f"{source}_{i}")
        
            # Create the initial document
            doc = Document(
                page_content=text,
                metadata=metadata
            )
            documents_to_process.append(doc)

    # 3. SPLIT ALL DOCUMENTS (Website AND Social)
    if documents_to_process:
        logger.info(f"Splitting {len(documents_to_process)} raw {source} items...")
        split_docs = text_splitter.split_documents(documents_to_process)
        
        logger.info(f"Ingesting {len(split_docs)} split chunks ({source}) into ChromaDB...")
        vector_store.add_documents(documents=split_docs)
        logger.info(f"{source} data successfully stored!")
        return len(split_docs)
    else:
        logger.warning(f"No valid documents found to ingest for {source}.")
        return 0

# Service functions
async def get_raw_chunks(query: str, k: int = 5) -> List[DocumentResult]:
    """
    Executes the synchronous retrieval method in a separate thread.
    """
    logger.info(f"Chroma Service: Received query: {query}")
    if not retriever:
        logger.error("Retriever not available.")
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

async def get_formatted_chunks(query: str, k: int = 5) -> str:
    """
    Gets relevant documents, removes duplicates based on content, and formats them into a single string.
    """
    logger.info(f"Chroma Service: Received formatted query: {query}")
    if not retriever:
        logger.error("Retriever not available.")
        return "Vector store retriever is not initialized."
    
    docs: List[Document] = await asyncio.to_thread(
        retriever.get_relevant_documents,
        query,
        k=k
    )
    
    if not docs:
        logger.info("No relevant information found in the vector database.")
        return "No relevant information found in the vector database."
    
    # Deduplication logic
    seen_contents = set()
    unique_docs = []
    for doc in docs:
        content_key = doc.page_content.strip().lower() 
        if content_key not in seen_contents:
            seen_contents.add(content_key)
            unique_docs.append(doc)
        
    return format_docs(unique_docs) 

# Admin service functions
def run_chroma_ingestion() -> int:
    """
    Loads all specified data files and ingests them into ChromaDB.
    """
    logger.info("--- Chroma Service: Running Full Data Ingestion ---")
    
    website_json_path = os.path.join(DATA_DIR, "website_data.json")
    logger.info(f"Loading website data from: {website_json_path}")
    website_json = load_json_data(website_json_path)
    
    linkedin_json_path = os.path.join(DATA_DIR, "linkedin_data.json")
    logger.info(f"Loading linkedin data from: {linkedin_json_path}")
    linkedin_json = load_json_data(linkedin_json_path)

    facebook_json_path = os.path.join(DATA_DIR, "facebook_data.json")
    logger.info(f"Loading facebook data from: {facebook_json_path}")
    facebook_json = load_json_data(facebook_json_path)

    tiktok_json_path = os.path.join(DATA_DIR, "tiktok_data.json")
    logger.info(f"Loading tiktok data from: {tiktok_json_path}")
    tiktok_json = load_json_data(tiktok_json_path)

    website_data = website_json.get("data", []) if isinstance(website_json, dict) else website_json
    linkedin_data = linkedin_json.get("data", []) if isinstance(linkedin_json, dict) else linkedin_json
    facebook_data = facebook_json.get("data", []) if isinstance(facebook_json, dict) else facebook_json
    tiktok_data = tiktok_json.get("data", []) if isinstance(tiktok_json, dict) else tiktok_json

    total_added = 0
    
    # Unified Ingestion calls
    total_added += ingest_data(website_data, "website")
    total_added += ingest_data(linkedin_data, "linkedin")
    total_added += ingest_data(facebook_data, "facebook")
    total_added += ingest_data(tiktok_data, "tiktok")

    try:
        count_result = vector_store._collection.count()
        logger.info(f"\n--- Ingestion Complete ---")
        logger.info(f"Total items in ChromaDB: {count_result}")
        return count_result
    except Exception as e:
        logger.error(f"Error counting items in collection: {e}")
        return total_added

def run_clear_chroma():
    """
    Deletes all data from the 'enterprise_data' collection.
    """
    logger.info("--- Chroma Service: Clearing 'enterprise_data' collection ---")
    try:
        temp_vector_store = Chroma(
            collection_name="enterprise_data",
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR
        )
        temp_vector_store.delete_collection()
        logger.info("Collection deleted.")
        
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
        
        logger.info("Collection re-created with new instance.")
        return "Collection 'enterprise_data' cleared and re-created successfully."
    except Exception as e:
        logger.error(f"Error clearing collection: {e}")
        raise e            

logger.info("ChromaDB Service file loaded.")