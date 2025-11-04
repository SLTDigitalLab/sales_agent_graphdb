from fastapi import APIRouter
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import Optional

# Importing the service functions and models
from api.services import chat_service
from api.routers.core import QueryRequest, QueryResponse, ClearRequest, ClearResponse 

# Define the router with the version prefix and tag
router = APIRouter(prefix="/v1", tags=["Conversational Agent"])

# --- CHAT ENDPOINT: STREAMING ---
@router.post("/chat/stream")
async def handle_chat_stream(query: QueryRequest):
    return StreamingResponse(
        chat_service.stream_chat_generator(query.session_id, query.question),
        media_type="text/event-stream"
    )

# --- CHAT ENDPOINT: SYNCHRONOUS ---
@router.post("/chat", response_model=QueryResponse)
async def handle_chat(query: QueryRequest):
    response_data = await chat_service.get_full_response(query.session_id, query.question)
    return QueryResponse(answer=response_data['answer'])

# --- CHAT ENDPOINT: CLEAR HISTORY ---
@router.post("/chat/clear", response_model=ClearResponse)
async def clear_chat_history(query: ClearRequest):
    message = chat_service.clear_session_history(query.session_id)
    return ClearResponse(message=message)