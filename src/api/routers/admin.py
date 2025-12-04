from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from src.api.services.config_manager import load_config, save_config
# UPDATED IMPORTS: Import the specific split functions
from src.api.services.scraper_runner import run_general_scraping, run_product_scraping
from src.api.services import db_service, neo4j_service

router = APIRouter(prefix="/admin", tags=["admin"])

class ConfigUpdate(BaseModel):
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    products_url: Optional[str] = None # Added this field

@router.get("/status")
async def admin_status():
    """Check if admin system is operational."""
    config = load_config()
    return {
        "status": "operational",
        "config_loaded": bool(config),
        "endpoints": [
            "/admin/config (GET/POST)",
            "/admin/trigger-scraper (POST)",     # General Scraper
            "/admin/scrape-products (POST)",     # Product Scraper (New)
            "/admin/ingest-chroma (POST)",
            "/admin/clear-chroma (DELETE)",
            "/admin/ingest-neo4j (POST)",
            "/admin/status (GET)"
        ]
    }

@router.get("/config")
async def get_config():
    """Retrieve current scraping configuration (URLs)."""
    config = load_config()
    return config

@router.post("/config")
async def update_config(update: ConfigUpdate):
    """Update scraping configuration (URLs)."""
    config = load_config()
    for key, value in update.dict().items():
        if value is not None:
            config[key] = value
    save_config(config)
    return {"message": "Configuration updated successfully", "config": config}

@router.post("/trigger-scraper")
async def trigger_scraper():
    """Trigger General Scraping (Website, FB, LinkedIn, TikTok)."""
    try:
        # Calls the lightweight function
        results = run_general_scraping()
        return {
            "message": "General scraping completed",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@router.post("/scrape-products")
async def scrape_products():
    """Trigger Product Scraping (Selenium) - Saves to CSV."""
    try:
        # Calls the heavy selenium function
        results = run_product_scraping()
        return {
            "message": "Product scraping completed",
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product scraping failed: {str(e)}")

# Database Management Endpoints
@router.post("/ingest-chroma")
async def ingest_chroma_data():
    """Ingest scraped data into ChromaDB."""
    print("--- Admin API: Received request to ingest ChromaDB data ---")
    try:
        items_added = db_service.run_chroma_ingestion()
        return {
            "message": "ChromaDB ingestion successful.",
            "items_added": items_added
        }
    except Exception as e:
        print(f"Error during ChromaDB ingestion: {e}")
        return {
            "message": f"ChromaDB ingestion failed: {str(e)}",
            "error": str(e),
            "status": "error"
        }

@router.delete("/clear-chroma")
async def clear_chroma_data():
    """Clear all data from ChromaDB."""
    print("--- Admin API: Received request to clear ChromaDB ---")
    try:
        message = db_service.run_clear_chroma()
        return {
            "message": message,
            "items_added": 0
        }
    except Exception as e:
        print(f"Error clearing ChromaDB: {e}")
        return {
            "message": f"ChromaDB clearing failed: {str(e)}",
            "error": str(e),
            "status": "error"
        }

@router.post("/ingest-neo4j")
async def ingest_neo4j_data():
    """Ingest product data into Neo4j."""
    print("--- Admin API: Received request to ingest Neo4j data ---")
    try:
        # This reads the products.csv created by /scrape-products and loads it
        processed_count = neo4j_service.run_neo4j_ingestion()
        return {
            "message": "Neo4j ingestion successful.",
            "processed_count": processed_count
        }
    except Exception as e:
        print(f"Error during Neo4j ingestion: {e}")
        raise HTTPException(status_code=500, detail=str(e))