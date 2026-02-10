from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel
from typing import Optional, List 
from sqlalchemy.orm import Session
from ..services.email_service import send_order_request_email
from src.api.db.sessions import get_db
from src.api.db.models import Product, Order, OrderItem, OrderStatus, Customer
from src.api.deps import get_current_customer

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/email", tags=["Email"])

class ProductItem(BaseModel):
    product_name: str
    quantity: int

class OrderRequest(BaseModel):
    items: List[ProductItem]
    # We still accept these for the email body, but we link the order to the logged-in user ID
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: Optional[str] = None
    notes: Optional[str] = None

@router.post("/order-request")
async def submit_order_request(
    request: OrderRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_customer) # <--- NEW: Require Login
):
    """
    Receives order request from Chat, creates DB Order record, reduces stock, and sends email.
    """
    logger.info(f"Processing order request for User ID: {current_user.id} ({current_user.email})")

    try:
        # 1. Create the Order Shell
        new_order = Order(
            customer_id=current_user.id,
            status=OrderStatus.PROCESSING,
            total_amount=0.0 # Will calculate below
        )
        db.add(new_order)
        db.flush() # Flush to generate new_order.id

        total_amount = 0.0
        items_processed = []

        # 2. Process Items
        for item in request.items:
            # Look for the product by exact name match (Case Insensitive recommended)
            product = db.query(Product).filter(Product.name.ilike(item.product_name)).first()

            if not product:
                logger.warning(f"Product not found: {item.product_name}")
                continue 

            # Check Stock
            if product.stock_quantity < item.quantity:
                raise HTTPException(status_code=400, detail=f"Insufficient stock for {product.name}. Available: {product.stock_quantity}")
            
            # Deduct Stock
            product.stock_quantity -= item.quantity
            
            # Calculate Price
            line_total = float(product.price) * item.quantity
            total_amount += line_total

            # Create Order Item
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                sku=product.sku,
                quantity=item.quantity,
                unit_price=product.price
            )
            db.add(order_item)
            items_processed.append(order_item)
            
            logger.info(f"Added item {product.name} to Order #{new_order.id}")

        # 3. Update Order Total & Commit
        if not items_processed:
            raise HTTPException(status_code=400, detail="No valid products found to order.")

        new_order.total_amount = total_amount
        db.commit()
        db.refresh(new_order)

        logger.info(f"Order #{new_order.id} committed successfully. Total: {total_amount}")

        # 4. Trigger Email in Background
        email_payload = request.dict()
        email_payload['order_id'] = new_order.id
        background_tasks.add_task(send_order_request_email, email_payload)

        return {"message": f"Order #{new_order.id} placed successfully!", "order_id": new_order.id}

    except HTTPException as he:
        db.rollback()
        raise he
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing order request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error while processing order.")

logger.info("Email router with DB Persistence loaded.")