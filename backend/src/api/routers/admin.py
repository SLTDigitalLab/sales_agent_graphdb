from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import Optional, List, Union
from src.api.services.config_manager import load_config, save_config
from src.api.services.scraper_runner import run_general_scraping, run_product_scraping
from src.api.services import db_service, neo4j_service
from src.api.deps import get_current_user, get_current_admin

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(get_current_admin)])

class ConfigUpdate(BaseModel):
    # Accept List[str] OR str 
    website_urls: Optional[Union[List[str], str]] = None 
    product_urls: Optional[Union[List[str], str]] = None
    
    # Legacy fields 
    website_url: Optional[str] = None
    products_url: Optional[str] = None
    
    # Social Media
    linkedin_url: Optional[str] = None
    facebook_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    
    # Dynamic Email Target
    target_email: Optional[str] = None 

    # Validator to check for '@' symbol
    @validator('target_email')
    def validate_email_format(cls, v):
        if v is not None and "@" not in v:
            raise ValueError('Invalid email format. Address must contain "@".')
        return v

@router.get("/status")
async def admin_status():
    """Check if admin system is operational."""
    config = load_config()
    return {
        "status": "operational",
        "config_loaded": bool(config),
        "endpoints": [
            "/admin/config (GET/POST)",
            "/admin/trigger-scraper (POST)",
            "/admin/scrape-products (POST)",
            "/admin/ingest-chroma (POST)",
            "/admin/clear-chroma (DELETE)",
            "/admin/ingest-neo4j (POST)",
            "/admin/status (GET)"
        ]
    }

@router.get("/config")
async def get_config():
    """Retrieve current scraping configuration."""
    return load_config()

@router.post("/config")
async def update_config(update: ConfigUpdate):
    """Update scraping configuration."""
    logger.info("Received request to update scraper configuration.")
    try:
        config = load_config()
        
        update_data = update.dict(exclude_unset=True)
        
        # Merge updates into existing config
        for key, value in update_data.items():
            config[key] = value
            
        save_config(config)
        return {"message": "Configuration updated successfully", "config": config}
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save configuration")

# --- SCRAPER ACTIONS ---

@router.post("/trigger-scraper")
async def trigger_scraper():
    """
    Trigger General Scraping (Website List + Social Media).
    This does NOT run the heavy product scraper.
    """
    logger.info("Admin triggered General Scraping.")
    try:
        results = run_general_scraping()
        return {
            "message": "General scraping completed", 
            "results": results
        }
    except Exception as e:
        logger.error(f"General scraping failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"General scraping failed: {str(e)}")

@router.post("/scrape-products")
async def scrape_products():
    """
    Trigger Product Scraping (Selenium).
    This saves to CSV but does NOT ingest to DB.
    """
    logger.info("Admin triggered Product Scraping.")
    try:
        results = run_product_scraping()
        return {
            "message": "Product scraping completed", 
            "results": results
        }
    except Exception as e:
        logger.error(f"Product scraping failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Product scraping failed: {str(e)}")

# --- DATABASE ACTIONS ---

@router.post("/ingest-neo4j")
async def ingest_neo4j_data():
    """Ingest the scraped products.csv into Neo4j."""
    logger.info("--- Admin API: Received request to ingest Neo4j data ---")
    try:
        count = neo4j_service.run_neo4j_ingestion()
        return {
            "message": "Neo4j ingestion successful.",
            "processed_count": count
        }
    except Exception as e:
        logger.error(f"Error during Neo4j ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest-chroma")
async def ingest_chroma_data():
    """Ingest website/social data into ChromaDB (Vector DB)."""
    logger.info("--- Admin API: Received request to ingest ChromaDB data ---")
    try:
        items_added = db_service.run_chroma_ingestion()
        return {
            "message": "ChromaDB ingestion successful.",
            "items_added": items_added
        }
    except Exception as e:
        logger.error(f"Error during ChromaDB ingestion: {e}", exc_info=True)
        return {
            "message": f"ChromaDB ingestion failed: {str(e)}",
            "error": str(e),
            "status": "error"
        }

@router.delete("/clear-chroma")
async def clear_chroma_data():
    """Clear all data from ChromaDB."""
    logger.info("--- Admin API: Received request to clear ChromaDB ---")
    try:
        message = db_service.run_clear_chroma()
        return {
            "message": message,
            "items_added": 0
        }
    except Exception as e:
        logger.error(f"Error clearing ChromaDB: {e}", exc_info=True)
        return {
            "message": f"ChromaDB clearing failed: {str(e)}",
            "error": str(e),
            "status": "error"
        }
    
@router.delete("/clear-neo4j")
async def clear_neo4j_data():
    """Clear all nodes and relationships from Neo4j."""
    logger.info("--- Admin API: Received request to clear Neo4j ---")
    try:
        message = neo4j_service.run_clear_neo4j() 
        return {
            "message": message,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error clearing Neo4j: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))