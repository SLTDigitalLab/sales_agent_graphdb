import os
import json
import asyncio
from typing import List, Dict, Optional
from fastapi.responses import StreamingResponse

# LangChain Redis History
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    from .agent_graph import app as agent_app 
except ImportError as e:
    logger.warning(f"Could not import agent_graph.app: {e}. Ensure agent_graph.py is in src/api/services/")
    agent_app = None

# Get Redis URL from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

def get_redis_history(session_id: str) -> RedisChatMessageHistory:
    """
    Connects to Redis and retrieves the chat history for a specific session.
    Sets a TTL (Time-To-Live) of 86400 seconds (24 hours) to prevent memory bloating.
    """
    return RedisChatMessageHistory(session_id, url=REDIS_URL, ttl=86400)


# --- Core Logic Functions ---

async def stream_chat_generator(session_id: str, question: str, user_id: Optional[int] = None):
    """Asynchronous generator to stream tokens from the LangGraph agent."""
    if not agent_app:
        logger.error("Attempted to stream chat, but Agent is not initialized.")
        yield f"data: {json.dumps({'content': 'Agent not initialized.'})}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
        return

    # 1. Pull existing history from Redis
    history_db = get_redis_history(session_id)
    current_chat_history = history_db.messages
    
    inputs = {
        "question": question, 
        "chat_history": current_chat_history,
        "user_id": user_id 
    }
    
    final_answer_tokens = []
    
    try:
        async for chunk in agent_app.astream(inputs, stream_mode="updates"):
            if 'generate' in chunk:
                message_content = chunk['generate'].get('generation')
                if isinstance(message_content, str):
                    token = message_content
                    final_answer_tokens.append(token)
                    yield f"data: {json.dumps({'content': token})}\n\n"
        
        final_answer = "".join(final_answer_tokens)
        
        # 2. Save the new turn back to Redis
        if final_answer:
            history_db.add_user_message(question)
            history_db.add_ai_message(final_answer)
            logger.info(f"Saved turn to Redis for session {session_id}")
        
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"

    except Exception as e:
        logger.error(f"Error during streaming generation: {e}", exc_info=True)
        yield f"data: {json.dumps({'content': 'Error generating response.'})}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"


async def get_full_response(session_id: str, question: str, user_id: Optional[int] = None):
    """Invokes the agent synchronously (waits for full response)."""
    if not agent_app:
        logger.error("Attempted to get full response, but Agent is not initialized.")
        return {"answer": "Agent not initialized. Check server logs."}
        
    # 1. Pull existing history from Redis
    history_db = get_redis_history(session_id)
    current_chat_history = history_db.messages
    
    inputs = {
        "question": question, 
        "chat_history": current_chat_history,
        "user_id": user_id 
    }
    
    try:
        final_state = await agent_app.ainvoke(inputs) 
        answer = final_state.get("generation", "Sorry, I couldn't generate a response.")
        
        # 2. Save the new turn back to Redis
        history_db.add_user_message(question)
        history_db.add_ai_message(answer)
        logger.info(f"Saved turn to Redis for session {session_id}")

        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error during synchronous generation: {e}", exc_info=True)
        return {"answer": "Sorry, an internal error occurred."}
    

def clear_session_history(session_id: str):
    """Clears the chat history for a specific session ID from Redis."""
    try:
        history_db = get_redis_history(session_id)
        history_db.clear()
        logger.info(f"History for session {session_id} wiped from Redis.")
        return f"History for session {session_id} cleared."
    except Exception as e:
        logger.error(f"Failed to clear Redis history: {e}")
        return f"Failed to clear history for session {session_id}."

logger.info("Chat Service (Redis Enabled) file loaded.")