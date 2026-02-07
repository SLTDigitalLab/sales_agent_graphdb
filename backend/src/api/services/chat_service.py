from typing import List, Dict, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json
import asyncio
from fastapi.responses import StreamingResponse

# IMPORT LOGGER
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

try:
    from .agent_graph import app as agent_app 
except ImportError as e:
    logger.warning(f"Could not import agent_graph.app: {e}. Ensure agent_graph.py is in src/api/services/")
    agent_app = None


# chat History Storage
chat_histories: Dict[str, List[BaseMessage]] = {}


# Core Logic Functions

async def stream_chat_generator(session_id: str, question: str, user_id: Optional[int] = None):
    """
    Asynchronous generator to stream tokens from the LangGraph agent.
    """
    if not agent_app:
        logger.error("Attempted to stream chat, but Agent is not initialized.")
        yield f"data: {json.dumps({'content': 'Agent not initialized.'})}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
        return

    current_chat_history = chat_histories.get(session_id, [])
    
    # --- UPDATED INPUTS with user_id ---
    inputs = {
        "question": question, 
        "chat_history": current_chat_history,
        "user_id": user_id  # <--- Pass to Agent State
    }
    
    final_answer_tokens = []
    
    # Stream from LangGraph
    try:
        # Note: Using stream_mode="messages" or "values" depending on graph setup. 
        # Since we use 'generate' node in graph, iterating over updates is safer.
        async for chunk in agent_app.astream(inputs, stream_mode="updates"):
            
            # Check for generation output
            if 'generate' in chunk:
                message_content = chunk['generate'].get('generation')
                
                # If content is a full string (since your 'generate' node returns full string)
                if isinstance(message_content, str):
                    # In this specific graph setup, 'generate' node returns the FULL answer at once, 
                    # not tokens. So we yield it all.
                    token = message_content
                    final_answer_tokens.append(token)
                    yield f"data: {json.dumps({'content': token})}\n\n"
        
        # Update history
        # Since 'generate' node updates history in state, we should grab it from there ideally,
        # but for simplicity in streaming, we append the result we got.
        final_answer = "".join(final_answer_tokens)
        if final_answer:
            updated_history = current_chat_history + [HumanMessage(content=question), AIMessage(content=final_answer)]
            chat_histories[session_id] = updated_history
        
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"

    except Exception as e:
        logger.error(f"Error during streaming generation: {e}", exc_info=True)
        yield f"data: {json.dumps({'content': 'Error generating response.'})}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"


async def get_full_response(session_id: str, question: str, user_id: Optional[int] = None):
    """
    Invokes the agent synchronously (waits for full response).
    """
    if not agent_app:
        logger.error("Attempted to get full response, but Agent is not initialized.")
        return {"answer": "Agent not initialized. Check server logs."}
        
    current_chat_history = chat_histories.get(session_id, [])
    
    # --- UPDATED INPUTS with user_id ---
    inputs = {
        "question": question, 
        "chat_history": current_chat_history,
        "user_id": user_id  # <--- Pass to Agent State
    }
    
    try:
        final_state = await agent_app.ainvoke(inputs) 
        
        answer = final_state.get("generation", "Sorry, I couldn't generate a response.")
        updated_history = final_state.get("chat_history", [])

        chat_histories[session_id] = updated_history
        return {"answer": answer}
    except Exception as e:
        logger.error(f"Error during synchronous generation: {e}", exc_info=True)
        return {"answer": "Sorry, an internal error occurred."}
    

def clear_session_history(session_id: str):
    """
    Clears the chat history for a specific session ID.
    """
    if session_id in chat_histories:
        del chat_histories[session_id]
        logger.info(f"History for session {session_id} cleared.")
        return f"History for session {session_id} cleared."
    else:
        logger.warning(f"Attempted to clear history for non-existent session {session_id}.")
        return f"No history found for session {session_id}."

logger.info("Chat Service file loaded.")