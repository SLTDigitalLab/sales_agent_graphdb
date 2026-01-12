import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.api.services.neo4j_service import graph, neo4j_available 

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/db/graph", tags=["Neo4j Products"])

class ProductItem(BaseModel):
    sku: str
    name: str
    price: float
    category_name: str

class ProductListResponse(BaseModel):
    products: List[ProductItem]

@router.get("/products-for-order-form", response_model=ProductListResponse)
async def get_products_for_order_form():
    """
    Retrieves a list of products from Neo4j suitable for the order form dropdown.
    Returns products with their names, prices, SKUs, and associated category names.
    """
    logger.info("Received request for products for order form.")
    
    if not neo4j_available or graph is None:
        logger.warning("Neo4j is unavailable. Returning empty product list.")
        return {"products": []} 

    try:
        cypher_query = """
        MATCH (p:Product)-[:IN_CATEGORY]->(c:Category)
        RETURN p.sku AS sku, p.name AS name, p.price AS price, c.name AS category_name
        ORDER BY c.name, p.name
        """

        # Run the blocking synchronous graph.query in a separate thread
        result = await asyncio.to_thread(graph.query, cypher_query)
    
        products_list = []
        for record in result:
            product_item = ProductItem(
                sku=record.get('sku', ''),
                name=record.get('name', ''),
                price=record.get('price', 0.0), 
                category_name=record.get('category_name', '')
            )
            products_list.append(product_item)

        return ProductListResponse(products=products_list)

    except Exception as e:
        logger.error(f"Error fetching products for order form from Neo4j: {e}", exc_info=True)
        return ProductListResponse(products=[])

logger.info("Neo4j Products for Order Form Router loaded.")