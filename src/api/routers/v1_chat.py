from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from typing import Optional

# IMPORT LOGGER
from src.utils.logging_config import get_logger

# Importing the service functions and models
from ..services import chat_service 
from .core import QueryRequest, QueryResponse, ClearRequest, ClearResponse

logger = get_logger(__name__)

# Define the router 
router = APIRouter(prefix="/v1", tags=["Conversational Agent"])

# --- CHAT ENDPOINT: STREAMING ---
@router.post("/chat/stream")
async def handle_chat_stream(query: QueryRequest):
    logger.info(f"Received STREAM chat request for session: {query.session_id}")
    try:
        return StreamingResponse(
            chat_service.stream_chat_generator(query.session_id, query.question),
            media_type="text/event-stream"
        )
    except Exception as e:
        logger.error(f"Error in chat stream endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error during streaming.")

# --- CHAT ENDPOINT: SYNCHRONOUS ---
@router.post("/chat", response_model=QueryResponse)
async def handle_chat(query: QueryRequest):
    logger.info(f"Received SYNC chat request for session: {query.session_id}")
    try:
        response_data = await chat_service.get_full_response(query.session_id, query.question)
        return QueryResponse(answer=response_data['answer'])
    except Exception as e:
        logger.error(f"Error in sync chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error during chat processing.")

# --- CHAT ENDPOINT: CLEAR HISTORY ---
@router.post("/chat/clear", response_model=ClearResponse)
async def clear_chat_history(query: ClearRequest):
    logger.info(f"Received CLEAR history request for session: {query.session_id}")
    try:
        message = chat_service.clear_session_history(query.session_id)
        return ClearResponse(message=message)
    except Exception as e:
        logger.error(f"Error clearing history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to clear chat history.")