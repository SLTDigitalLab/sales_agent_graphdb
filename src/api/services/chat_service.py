from typing import List, Dict
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
import json
import asyncio
from fastapi.responses import StreamingResponse

# ⬅️ IMPORT YOUR AGENT FROM THE PARENT DIRECTORY 
# Assuming agent_graph.py is in the project root
try:
    from agent_graph import app as agent_app 
except ImportError:
    # Handle the case where the import fails during initial setup
    print("WARNING: Could not import agent_graph.app. Ensure agent_graph.py is in the project root.")
    agent_app = None


# --- Chat History Storage (Centralized) ---
chat_histories: Dict[str, List[BaseMessage]] = {}


# --- Core Logic Functions ---

async def stream_chat_generator(session_id: str, question: str):
    """
    Asynchronous generator to stream tokens from the LangGraph agent.
    """
    if not agent_app:
        yield f"data: {json.dumps({'content': 'Agent not initialized.'})}\n\n"
        yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"
        return

    current_chat_history = chat_histories.get(session_id, [])
    inputs = {"question": question, "chat_history": current_chat_history}
    final_answer_tokens = []
    
    # 1. Stream from LangGraph
    async for chunk in agent_app.astream(inputs, stream_mode="messages"):
        if 'generate' in chunk:
            message_chunk = chunk['generate'].get('generation')
            if message_chunk and message_chunk.content:
                token = message_chunk.content
                final_answer_tokens.append(token)
                yield f"data: {json.dumps({'content': token})}\n\n"
    
    # 2. Update History (after stream finishes)
    final_answer = "".join(final_answer_tokens)
    updated_history = current_chat_history + [HumanMessage(content=question), AIMessage(content=final_answer)]
    chat_histories[session_id] = updated_history
    
    yield f"data: {json.dumps({'content': '[DONE]'})}\n\n"


async def get_full_response(session_id: str, question: str):
    """
    Invokes the agent synchronously (waits for full response).
    """
    if not agent_app:
        return {"answer": "Agent not initialized. Check server logs."}
        
    current_chat_history = chat_histories.get(session_id, [])
    inputs = {"question": question, "chat_history": current_chat_history}
    
    final_state = await agent_app.ainvoke(inputs) 
    
    # Extract data using the confirmed keys
    answer = final_state.get("generation", "Sorry, I couldn't generate a response.")
    updated_history = final_state.get("chat_history", [])

    # Update history
    chat_histories[session_id] = updated_history
    return {"answer": answer}
    

def clear_session_history(session_id: str):
    """
    Clears the chat history for a specific session ID.
    """
    if session_id in chat_histories:
        del chat_histories[session_id]
        return f"History for session {session_id} cleared."
    else:
        return f"No history found for session {session_id}."