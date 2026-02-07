from typing import List, Optional, Dict, Any
from langchain_core.tools import tool
from sqlalchemy.orm import Session
from sqlalchemy import and_

# --- INTERNAL IMPORTS ---
from src.api.db.sessions import SessionLocal
from src.api.db.models import Product, Order, OrderItem, OrderStatus, Customer
from src.api.services.neo4j_service import run_graph_query

# IMPORT LOGGER
from src.utils.logging_config import get_logger
logger = get_logger(__name__)

# ==========================================
# TOOL 1: PRODUCT SEARCH (The "Eyes")
# ==========================================
@tool
def search_products_tool(query: str) -> str:
    """
    Useful for finding products, checking prices, and getting specifications.
    Input should be a natural language question like "Do you have any routers?" or "What is the price of the Tedi Robot?".
    """
    logger.info(f"Agent Tool Invoked: search_products_tool with query='{query}'")
    return run_graph_query(query)

# ==========================================
# TOOL 2: STOCK CHECKER (The "Inventory Manager")
# ==========================================
@tool
def check_stock_tool(product_name_or_id: str) -> str:
    """
    Useful for checking if a specific product is in stock.
    Input can be a Product ID (e.g., "12") or a fuzzy Name (e.g., "Tedi Robot").
    Returns the exact stock quantity.
    """
    logger.info(f"Agent Tool Invoked: check_stock_tool for '{product_name_or_id}'")
    db: Session = SessionLocal()
    try:
        # 1. Try finding by ID first
        if product_name_or_id.isdigit():
            product = db.query(Product).filter(Product.id == int(product_name_or_id)).first()
            if product:
                 return _format_stock_response(product)
        
        # 2. Try Exact Fuzzy Search (The strict one)
        # e.g. Input: "Tenda F3" -> Matches "Tenda F3 Router"
        product = db.query(Product).filter(Product.name.ilike(f"%{product_name_or_id}%")).first()
        if product:
            logger.info(f"Stock Found (Exact Match): {product.name}")
            return _format_stock_response(product)

        # 3. Fallback: Search by "Significant Terms"
        # If Input is "Tenda F3 Router 300Mbps" but DB is "Tenda F3", the above fails.
        # We split the string and try to match the first few words.
        words = product_name_or_id.split()
        if len(words) > 1:
            # Try matching just the first 2 words (e.g. "Tenda F3")
            short_search = f"%{words[0]}% {words[1]}%" # Matches "...Tenda... ...F3..."
            # Note: This is a loose heuristic, but effective for e-commerce
            product = db.query(Product).filter(
                and_(
                    Product.name.ilike(f"%{words[0]}%"),
                    Product.name.ilike(f"%{words[1]}%")
                )
            ).first()
            
            if product:
                logger.info(f"Stock Found (Fallback Match 2 words): {product.name}")
                return _format_stock_response(product)

        # 4. Fallback: First word only (Desperate measure)
        if len(words) > 0:
            product = db.query(Product).filter(Product.name.ilike(f"%{words[0]}%")).first()
            if product:
                logger.info(f"Stock Found (Fallback Match 1 word): {product.name}")
                return _format_stock_response(product)

        return f"Error: Product '{product_name_or_id}' not found in the catalog."

    except Exception as e:
        logger.error(f"Stock check error: {e}", exc_info=True)
        return f"Error checking stock: {str(e)}"
    finally:
        db.close()

def _format_stock_response(product: Product) -> str:
    if product.stock_quantity > 0:
        return f"AVAILABLE: Product '{product.name}' (ID: {product.id}) has {product.stock_quantity} units in stock."
    else:
        return f"UNAVAILABLE: Product '{product.name}' is currently out of stock."
        
# ==========================================
# TOOL 3: ORDER PLACER (The "Cashier")
# ==========================================
def place_order_logic(user_id: int, product_id: int, quantity: int) -> str:
    """
    Internal logic to place an order.
    Executes an atomic transaction: checks stock -> deducts stock -> creates order.
    """
    logger.info(f"Agent Logic: Attempting to place order for User {user_id}, Product {product_id}, Qty {quantity}")
    
    db: Session = SessionLocal()
    try:
        # 1. Validate User
        user = db.query(Customer).filter(Customer.id == user_id).first()
        if not user:
            return "Error: User Authentication Failed. Cannot find user record."

        # 2. Validate Product & Stock
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            return f"Error: Product ID {product_id} not found."
        
        if product.stock_quantity < quantity:
            return f"Error: Insufficient stock. Only {product.stock_quantity} units available for '{product.name}'."

        # 3. Create Order (Atomic Transaction)
        total_price = float(product.price) * quantity
        
        new_order = Order(
            customer_id=user_id,
            status=OrderStatus.PROCESSING,
            total_amount=total_price
        )
        db.add(new_order)
        db.flush() # Generate ID

        # 4. Create Order Item
        order_item = OrderItem(
            order_id=new_order.id,
            product_id=product.id,
            quantity=quantity,
            unit_price=product.price
        )
        db.add(order_item)

        # 5. Deduct Stock
        product.stock_quantity -= quantity
        
        db.commit()
        logger.info(f"Agent Order Success: Order #{new_order.id} created.")
        
        return f"SUCCESS: Order #{new_order.id} placed for '{product.name}' (Qty: {quantity}). Total: Rs. {total_price}."

    except Exception as e:
        db.rollback()
        logger.error(f"Agent Order Failed: {e}", exc_info=True)
        return f"System Error: Transaction failed. {str(e)}"
    finally:
        db.close()