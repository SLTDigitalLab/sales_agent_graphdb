from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Dict, Any


# Models for Chat
class QueryRequest(BaseModel):
    session_id: str 
    question: str

class QueryResponse(BaseModel):
    answer: str

class ClearRequest(BaseModel):
    session_id: str

class ClearResponse(BaseModel):
    message: str

# Models for DB/Admin
class DbQueryRequest(BaseModel):
    question: str

class DbQueryResponse(BaseModel):
    result: str

class IngestResponse(BaseModel):
    message: str
    items_added: int

# Models for Vector Store
class VectorQueryRequest(BaseModel):
    question: str
    k: int = 3

class DocumentResult(BaseModel):
    page_content: str
    metadata: Dict[str, Any]

class RawChunksResponse(BaseModel):
    results: List[DocumentResult]

print("Core API models loaded.")


#Define Global/System router

router = APIRouter(tags=["Global/System"])

@router.get("/")
async def root():
    """Root endpoint for a general check."""
    return {"message": "AI Enterprise Agent API is running! Access docs at /docs or use /health."}

@router.get("/health")
async def health_check():
    """Health check endpoint, essential for deployment and monitoring."""
    return {"status": "ok", "service": "ai-enterprise-agent"}

print("Core API router loaded.")