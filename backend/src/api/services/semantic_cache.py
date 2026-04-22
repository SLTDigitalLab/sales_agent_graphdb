import os
import chromadb
from langchain_openai import OpenAIEmbeddings
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# --- THE FIX: Point EXACTLY to the shared chroma_data folder ---
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(script_dir, '..', '..', '..')
CHROMA_PERSIST_DIR = os.path.join(project_root, 'chroma_data')

# Ensure the directory exists (It will just hook into the existing one)
os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

# Initialize ONE unified PersistentClient pointing to the shared folder
chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# Use cosine similarity. This collection sits safely next to 'enterprise_data'
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
        query_embedding = embeddings.embed_query(question)
        
        results = cache_collection.query(
            query_embeddings=[query_embedding],
            n_results=1,
            include=["metadatas", "distances"]
        )

        if not results or not results["distances"] or len(results["distances"][0]) == 0:
            return None

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
    """Saves the question and response using upsert to avoid duplicate IDs."""
    try:
        query_embedding = embeddings.embed_query(query)
        doc_id = f"cache_{hash(query)}"
        
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
    """Wipes ONLY the semantic cache collection to prevent stale data."""
    global cache_collection
    try:
        # Safely delete ONLY the cache collection, keeping enterprise_data intact
        chroma_client.delete_collection(name="semantic_response_cache")
        
        # Recreate a fresh, empty collection
        cache_collection = chroma_client.get_or_create_collection(
            name="semantic_response_cache",
            metadata={"hnsw:space": "cosine"} 
        )
        logger.info("🗑️ Semantic Cache cleared (Collection cleanly recreated).")
        return True
    except Exception as e:
        logger.error(f"Error clearing semantic cache: {e}")
        return False