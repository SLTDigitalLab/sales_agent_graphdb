# src/api/routers/neo4j_products.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from src.api.services.neo4j_service import graph, neo4j_available 

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
    print("Neo4j Service: Received request for products for order form.")
    
    if not neo4j_available or graph is None:
        return {"products": []} # Return empty list if Neo4j is unavailable

    try:
        # Adjust this Cypher query based on your actual Neo4j schema
        # This query assumes Product nodes have 'sku', 'name', 'price' properties
        # and are connected to Category nodes via an 'IN_CATEGORY' relationship
        # Example query structure:
        cypher_query = """
        MATCH (p:Product)-[:IN_CATEGORY]->(c:Category)
        RETURN p.sku AS sku, p.name AS name, p.price AS price, c.name AS category_name
        ORDER BY c.name, p.name
        """

        result = graph.query(cypher_query)
        print(f"Neo4j query result for order form: {result}")

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
        print(f"Error fetching products for order form from Neo4j: {e}")
        return ProductListResponse(products=[])

print("Neo4j Products for Order Form Router loaded.")