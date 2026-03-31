import os
import chromadb
from langchain_openai import OpenAIEmbeddings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Define where to store the cache data locally
CACHE_DIR = os.path.join(os.getcwd(), "chroma_cache_data")
os.makedirs(CACHE_DIR, exist_ok=True)

# Initialize Chroma and Embeddings
chroma_client = chromadb.PersistentClient(path=CACHE_DIR)
embeddings = OpenAIEmbeddings(model="text-embedding-3-small") # Adjust model if needed

# Use cosine similarity (default is L2). Cosine is generally better for semantic text comparison.
cache_collection = chroma_client.get_or_create_collection(
    name="semantic_response_cache",
    metadata={"hnsw:space": "cosine"} 
)

def check_semantic_cache(question: str, threshold: float = 0.85) -> str | None:
    """
    Search for the question in ChromaDB.
    Returns the answer ONLY if (1 - distance) >= threshold.
    """
    try:
        # 1. Embed the incoming question
        query_embedding = embeddings.embed_query(question)
        
        # 2. Search cache
        results = cache_collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["metadatas", "distances"]
        )

        # 3. Check if we have any results
        if not results or not results["distances"] or len(results["distances"][0]) == 0:
            return None

        # 4. Calculate Similarity Score
        # In Cosine Space: Score 1.0 = identical, 0.0 = orthogonal
        distance = results["distances"][0][0]
        similarity_score = 1 - distance 

        logger.info(f"🔍 Cache Search: Score {similarity_score:.4f} | Threshold {threshold}")

        if similarity_score >= threshold:
            logger.info("🟢 Semantic Cache HIT!")
            return results['metadatas'][0][0].get("response")
        
        logger.info("🔴 Semantic Cache MISS: Score below threshold.")
        return None

    except Exception as e:
        logger.error(f"Error checking semantic cache: {e}")
        return None
    
def add_to_semantic_cache(query: str, response: str):
    """Saves the question and response. Uses upsert to avoid duplicate IDs."""
    try:
        query_embedding = embeddings.embed_query(query)
        doc_id = f"cache_{hash(query)}"
        
        # Use upsert instead of add to prevent "ID already exists" errors
        cache_collection.upsert(
            ids=[doc_id],
            embeddings=[query_embedding],
            documents=[query], 
            metadatas=[{"response": response}]
        )
        logger.info(f"💾 Saved/Updated cache for: {query[:50]}...")
    except Exception as e:
        logger.error(f"Error saving to semantic cache: {e}")

def clear_semantic_cache():
    """Wipes the entire semantic cache to prevent stale data."""
    global cache_collection
    try:
        # Delete the existing cache collection
        chroma_client.delete_collection(name="semantic_response_cache")
        
        # Recreate a fresh, empty collection with the same settings
        cache_collection = chroma_client.get_or_create_collection(
            name="semantic_response_cache",
            metadata={"hnsw:space": "cosine"} 
        )
        logger.info(" Semantic Cache cleared after data ingestion.")
        return True
    except Exception as e:
        logger.error(f"Error clearing semantic cache: {e}")
        return False