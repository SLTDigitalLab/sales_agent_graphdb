from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from src.api.db.sessions import get_db
from src.api.db.models import Order, OrderItem, Product, OrderStatus, Customer
from src.api.schemas import OrderCreate, OrderOut, OrderItemOut
from src.api.deps import get_current_customer

# IMPORT LOGGER
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.post("/", response_model=OrderOut)
def place_order(
    order_data: OrderCreate, 
    db: Session = Depends(get_db), 
    current_user: Customer = Depends(get_current_customer)
):
    """
    Creates a new order.
    1. Validates stock for all items.
    2. Deducts stock.
    3. Creates Order and OrderItems records.
    """
    logger.info(f"User {current_user.email} is attempting to place an order.")
    
    # 1. Validation
    total_amount = 0.0
    valid_items = []
    
    for item in order_data.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product ID {item.product_id} not found")
        
        if product.stock_quantity < item.quantity:
            raise HTTPException(status_code=400, detail=f"Not enough stock for '{product.name}'. Available: {product.stock_quantity}")
            
        total_amount += float(product.price) * item.quantity
        valid_items.append((product, item.quantity))

    # 2. Transaction
    try:
        new_order = Order(
            customer_id=current_user.id,
            status=OrderStatus.PROCESSING,
            total_amount=total_amount
        )
        db.add(new_order)
        db.flush() 
        
        # Create Items & Update Stock
        db_items = []
        for product, qty in valid_items:
            product.stock_quantity -= qty
            
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=product.id,
                quantity=qty,
                unit_price=product.price
            )
            db.add(order_item)
            db_items.append(order_item)
            
        db.commit()
        db.refresh(new_order)
        logger.info(f"Order #{new_order.id} placed successfully.")
        
        return OrderOut(
            id=new_order.id,
            customer_id=new_order.customer_id,
            status=new_order.status,
            total_amount=new_order.total_amount,
            created_at=new_order.created_at,
            items=[
                OrderItemOut(
                    product_id=item.product_id,
                    product_name=item.product.name,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                ) for item in new_order.items
            ]
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Order failed: {e}")
        raise HTTPException(status_code=500, detail="Transaction failed")

@router.get("/", response_model=List[OrderOut])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_customer)
):
    """Retrieve order history for the logged-in user."""
    orders = db.query(Order).filter(Order.customer_id == current_user.id).all()
    
    # Format response
    results = []
    for o in orders:
        results.append(OrderOut(
            id=o.id,
            customer_id=o.customer_id,
            status=o.status,
            total_amount=o.total_amount,
            created_at=o.created_at,
            items=[
                OrderItemOut(
                    product_id=i.product_id,
                    product_name=i.product.name,
                    quantity=i.quantity,
                    unit_price=i.unit_price
                ) for i in o.items
            ]
        ))
    return results