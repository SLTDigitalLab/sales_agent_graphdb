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
async def ingest_neo4j_data():
    """
    Triggers the ingestion of products.csv into Neo4j.
    This will WIPE and reload the graph data.
    """
    logger.info("Received request to ingest Neo4j data via Admin endpoint.")
    try:
        # Call the logic function from the service file
        items_added = neo4j_service.run_neo4j_ingestion() 
        return IngestResponse(message="Neo4j ingestion successful.", items_added=items_added)
    except Exception as e:
        logger.error(f"Error in /admin/ingest-neo4j: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

logger.info("Neo4j Router file loaded.")