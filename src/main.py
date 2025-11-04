from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import os
# Importing the state management variables
from api.services.chat_service import chat_histories 

# Importing Routers
from api.routers import v1_chat, db_utils, core 

# --- FastAPI Setup and CORS ---
api = FastAPI(
    title="AI Enterprise Agent API (v1)",
    description="API for interacting with the LangGraph agent."
)

ALLOWED_ORIGINS = [
    "http://localhost:5173", 
    "http://127.0.0.1:5173", 
    "http://localhost:5174", 
    "http://localhost:3000", 
]

api.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- Register Routers ---
# Note: Routers are registered in main.py, but their logic lives elsewhere.
api.include_router(core.router)      # / and /health
api.include_router(v1_chat.router)   # /v1/chat, /v1/chat/stream, etc.
api.include_router(db_utils.router)  # /db/vector/raw-chunks

print("FastAPI application initialized and routers included.")

# Run with: uvicorn main:api --reload