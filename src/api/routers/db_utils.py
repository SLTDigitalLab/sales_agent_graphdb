from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import asyncio

# Importing the service and necessary models
from api.services import db_service 
from api.routers.core import SearchRequest, SearchResponse 

# Define the router for DB Utilities
router = APIRouter(prefix="/db", tags=["Database Utilities"])

@router.post("/vector/raw-chunks", response_model=SearchResponse)
async def semantic_search_raw_chunks(request: SearchRequest):
    """
    Performs a direct semantic search against the Chroma vector store and 
    returns the raw document chunks with metadata.
    """
    results = await db_service.get_raw_chunks(request.query, request.k)
    return SearchResponse(results=results)