import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, validator
from typing import Optional, List, Union
from src.api.services.config_manager import load_config, save_config
from src.api.services.scraper_runner import run_general_scraping, run_product_scraping
from src.api.services import db_service, neo4j_service
from src.api.deps import get_current_user, get_current_admin
from src.api.schemas import ProductCreate, ProductUpdate, ProductOut, OrderOut, OrderStatusUpdate, CustomerOut

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

# --- PRODUCT MANAGEMENT ---

@router.get("/products", response_model=List[ProductOut])
async def get_all_products():
    """Fetch all products to display in the admin dashboard."""
    try:
        products = db_service.get_all_products()
        return products
    except Exception as e:
        logger.error(f"Failed to fetch all products: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve products")

@router.post("/products", response_model=ProductOut)
async def create_new_product(product_data: ProductCreate):
    """Create a new product in Postgres and sync it to Neo4j."""
    try:
        # 1. Save to PostgreSQL
        new_product = db_service.create_product_in_db(product_data)
        
        # 2. Sync to Neo4j Knowledge Graph
        neo4j_service.sync_single_product(new_product)
        
        return new_product
    except Exception as e:
        logger.error(f"Failed to create new product: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Creation failed: {str(e)}")

@router.get("/products/{sku}", response_model=ProductOut)
async def get_product_by_sku(sku: str):
    """Fetch a specific product from Postgres using its SKU."""
    product = db_service.get_product_by_sku(sku)
    if not product:
        raise HTTPException(status_code=404, detail=f"Product with SKU {sku} not found")
    return product

@router.patch("/products/{sku}", response_model=ProductOut)
async def update_product_by_sku(sku: str, update_data: ProductUpdate):
    """Update product and sync to Neo4j using SKU as the primary key."""
    try:
        # 1. Update PostgreSQL (Source of Truth)
        updated_product = db_service.update_product_in_db_by_sku(sku, update_data)
        if not updated_product:
            raise HTTPException(status_code=404, detail="Product not found")

        # 2. Sync to Neo4j (Sales Agent Knowledge)
        # The Neo4j service will use MERGE on the SKU to update the node
        neo4j_service.sync_single_product(updated_product)
        
        return updated_product
    except Exception as e:
        logger.error(f"Failed to update product {sku}: {e}")
        raise HTTPException(status_code=500, detail="Update failed")

@router.delete("/products/{sku}")
async def delete_product_by_sku(sku: str):
    """Remove product from both systems using SKU."""
    try:
        # Delete from Postgres
        deleted = db_service.delete_product_from_db_by_sku(sku)
        if not deleted:
            raise HTTPException(status_code=404, detail="Product not found in database")
        
        # Delete from Neo4j
        neo4j_service.delete_product_node(sku)
        
        return {"message": f"Product {sku} successfully removed."}
    except Exception as e:
        logger.error(f"Delete failed for {sku}: {e}")
        raise HTTPException(status_code=500, detail="Deletion failed")

# --- ORDER MANAGEMENT ---

from src.api.schemas import OrderOut, OrderStatusUpdate

@router.get("/orders", response_model=List[OrderOut])
async def get_all_orders():
    """Fetch all orders for the admin dashboard."""
    try:
        orders = db_service.get_all_orders()
        return orders
    except Exception as e:
        logger.error(f"Failed to fetch orders: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve orders")

@router.patch("/orders/{order_id}/status", response_model=OrderOut)
async def update_order_status(order_id: int, update_data: OrderStatusUpdate):
    """Update the processing status of an order."""
    try:
        updated_order = db_service.update_order_status(order_id, update_data.status)
        if not updated_order:
            raise HTTPException(status_code=404, detail=f"Order ID {order_id} not found")
        return updated_order
    except Exception as e:
        logger.error(f"Failed to update order {order_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to update order status")
    
# --- CUSTOMER MANAGEMENT ---

@router.get("/customers", response_model=List[CustomerOut])
async def get_all_customers():
    """Fetch all customers for the admin dashboard."""
    try:
        customers = db_service.get_all_customers()
        return customers
    except Exception as e:
        logger.error(f"Failed to fetch customers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve customers")