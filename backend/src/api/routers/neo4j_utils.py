from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# IMPORT LOGGER
from src.utils.logging_config import get_logger

# Import the service functions
from ..services import neo4j_service 

from .core import (
    DbQueryRequest,     
    DbQueryResponse, 
    IngestResponse
)

logger = get_logger(__name__)

# Create a new router
router = APIRouter()

# Define API endpoints

@router.post("/db/graph/query", response_model=DbQueryResponse, tags=["Database Utilities"])
async def query_graph(query: DbQueryRequest):
    """
    Receives a natural language question, queries the Neo4j graph, 
    and returns the synthesized answer.
    """
    logger.info(f"Received Graph DB query: {query.question}")
    try:
        # Call the logic function from the service file
        answer = neo4j_service.run_graph_query(query.question)
        return DbQueryResponse(result=answer) 
    except Exception as e:
        logger.error(f"Error in /db/graph/query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/ingest-neo4j", response_model=IngestResponse, tags=["Admin"])
async def ingest_master_data():
    """
    MASTER SYNC ENDPOINT:
    1. Reads 'backend/data/products.csv' (Golden Copy).
    2. Wipes & Reseeds Supabase SQL (Resetting IDs to 1).
    3. Wipes & Reseeds Neo4j AuraDB.
    
    WARNING: This deletes all existing products and orders in SQL!
    """
    logger.info("Received MASTER INGESTION request via Admin endpoint.")
    try:
        stats = neo4j_service.run_master_ingestion()
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
            
        msg = f"Sync Complete. SQL: {stats['sql_added']}, Neo4j: {stats['neo4j_added']} items."
        return IngestResponse(message=msg, items_added=stats['sql_added'])
        
    except Exception as e:
        logger.error(f"Error in /admin/ingest-neo4j: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

logger.info("Neo4j Router file loaded.")