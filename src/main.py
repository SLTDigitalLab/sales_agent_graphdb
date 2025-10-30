from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio 
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict

from .agent_graph import app as agent_app
from langchain_core.messages import BaseMessage

# Chat History Storage 
# Uses a simple in-memory dictionary to store chat histories by session ID. will reset when the server restarts.
chat_histories: Dict[str, List[BaseMessage]] = {}

#API models
class QueryRequest(BaseModel):
    session_id: str 
    question: str

class QueryResponse(BaseModel):
    answer: str

class ClearRequest(BaseModel):
    session_id: str

class ClearResponse(BaseModel):
    message: str


# FastAPI app instance
api = FastAPI(
    title="AI Enterprise Agent API",
    description="API for interacting with the LangGraph agent."
)

api.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite's default ports
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default dev server
        "http://localhost:5174",  # Alternative Vite port
        "http://localhost:3000",  # Alternative React port
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

@api.post("/chat", response_model=QueryResponse)
async def handle_chat(query: QueryRequest):
    """
    Receives a question and session_id, returns the agent's response.
    """
    print(f"--- Received Request ---")
    print(f"Session ID: {query.session_id}")
    print(f"Question: {query.question}")

    # History Management
    current_chat_history = chat_histories.get(query.session_id, [])

    inputs = {
        "question": query.question,
        "chat_history": current_chat_history
    }
    
    final_state = await agent_app.ainvoke(inputs)

    answer = final_state.get("generation", "Sorry, I couldn't generate a response.")
    updated_history = final_state.get("chat_history", [])

    chat_histories[query.session_id] = updated_history

    print(f"Agent answer: {answer}")
    return QueryResponse(answer=answer)

@api.post("/chat/clear", response_model=ClearResponse)
async def clear_chat_history(query: ClearRequest):
    """
    Clears the chat history for a given session_id.
    """
    if query.session_id in chat_histories:
        del chat_histories[query.session_id]
        print(f"Cleared history for session: {query.session_id}")
        return ClearResponse(message=f"History for session {query.session_id} cleared.")
    else:
        print(f"No history found to clear for session: {query.session_id}")
        return ClearResponse(message=f"No history found for session {query.session_id}.")


@api.get("/")
async def root():
    return {"message": "AI Enterprise Agent API is running!"}

print("FastAPI app created.")

