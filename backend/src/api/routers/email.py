from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List 
from sqlalchemy.orm import Session
from ..services.email_service import send_order_request_email
from src.api.db.sessions import get_db
from src.api.db.models import Product

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])

class ProductItem(BaseModel):
    product_name: str
    quantity: int

class OrderRequest(BaseModel):
    items: List[ProductItem]
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: Optional[str] = None
    notes: Optional[str] = None

@router.post("/order-request")
async def submit_order_request(
    request: OrderRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Receives order request, reduces stock in PostgreSQL, and sends email.
    """
    logger.info(f"Processing order request for: {request.customer_name}")

    try:
        # 1. Update Inventory in PostgreSQL
        for item in request.items:
            # Look for the product by name (matching your scraper logic)
            product = db.query(Product).filter(Product.name == item.product_name).first()

            if not product:
                logger.warning(f"Product not found: {item.product_name}")
                continue # Or raise HTTPException if you want to block the order

            # Check if enough stock exists
            if product.stock_quantity < item.quantity:
                logger.error(f"Insufficient stock for {product.name}. Available: {product.stock_quantity}, Requested: {item.quantity}")
                # Optional: Uncomment the line below to block orders if stock is low
                # raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}")
            
            # Reduce the stock
            product.stock_quantity -= item.quantity
            logger.info(f"Reduced stock for {product.name}. New total: {product.stock_quantity}")

        # Commit all stock changes at once
        db.commit()

        # 2. Trigger Email in Background
        background_tasks.add_task(send_order_request_email, request.dict())

        return {"message": "Stock updated and order request is being processed."}

    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing order request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while processing inventory.")

logger.info("Email router with inventory sync loaded.")