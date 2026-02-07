from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

from src.api.db.sessions import get_db
from src.api.db.models import Product
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/products", tags=["Products"])

@router.get("/search")
def search_product_details(
    query: str = Query(..., description="Product name to search for"),
    db: Session = Depends(get_db)
):
    """
    Search for a single product to display in the Canvas.
    Prioritizes exact matches, then falls back to partial matches.
    """
    logger.info(f"Canvas API: Searching for product details: '{query}'")
    
    # 1. Try Exact Match (Case Insensitive)
    product = db.query(Product).filter(Product.name.ilike(query)).first()
    
    # 2. If not found, try Partial Match
    if not product:
        product = db.query(Product).filter(Product.name.ilike(f"%{query}%")).first()
        
    # 3. If still not found, try splitting words (Fallback)
    if not product and " " in query:
        first_word = query.split(" ")[0]
        # Only try fallback if the word is substantial (len > 3) to avoid matching "The"
        if len(first_word) > 3:
            product = db.query(Product).filter(Product.name.ilike(f"%{first_word}%")).first()

    if not product:
        logger.warning(f"Product not found for query: '{query}'")
        raise HTTPException(status_code=404, detail="Product not found")

    # 4. Format the Image URL
    # If the DB has a full URL, use it. If it's missing, use a placeholder.
    image_url = product.image_url
    if not image_url or image_url.strip() == "":
        image_url = "https://via.placeholder.com/300?text=No+Image"
    
    # 5. Construct Response (Matching your Frontend ProductCanvas props)
    return {
        "id": product.id,
        "name": product.name,
        "price": float(product.price),
        "stock": product.stock_quantity,
        "description": product.description or "No description available.",
        "image": image_url,
        "specs": {
             "SKU": product.sku,
             "Category": product.category or "General"
        } 
    }