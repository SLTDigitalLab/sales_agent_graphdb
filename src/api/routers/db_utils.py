from fastapi import APIRouter, HTTPException
from typing import List

# Import the service functions
from ..services import db_service 

# Import shared models from .core
from .core import (
    VectorQueryRequest, 
    DbQueryResponse,    
    RawChunksResponse,
    IngestResponse  
)

# Create a new router
router = APIRouter(prefix="/db", tags=["Database Utilities"])

# Database Utility Endpoints
@router.post("/vector/search", response_model=DbQueryResponse)
async def search_vector_db(query: VectorQueryRequest):
    """
    Receives a natural language question, performs a semantic search,
    and returns the formatted result as a single string.
    
    This is the primary endpoint your agent's 'query_vector_db' node will call.
    """
    try:
        # Call the formatted chunk function from the service file
        answer = await db_service.get_formatted_chunks(query.question, k=query.k)
        return DbQueryResponse(result=answer)
    except Exception as e:
        print(f"Error in /db/vector/search: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/vector/raw-chunks", response_model=RawChunksResponse)
async def get_vector_chunks(query: VectorQueryRequest):
    """
    (Debug Endpoint)
    Receives a natural language question, performs a semantic search,
    and returns the raw, unformatted document chunks.
    """
    try:
        # Call the raw chunk function from the service file
        documents = await db_service.get_raw_chunks(query.question, k=query.k)
        return RawChunksResponse(results=documents)
    except Exception as e:
        print(f"Error in /db/vector/raw-chunks: {e}")
        raise HTTPException(status_code=500, detail=str(e))
