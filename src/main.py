from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import os
from dotenv import load_dotenv 

# SETUP LOGGING
from .utils.logging_config import setup_logging, get_logger

# Initialize logging configuration immediately
setup_logging()
logger = get_logger(__name__)

load_dotenv()
from .api import auth
from .api.services.chat_service import chat_histories 

# Importing Routers
from .api.routers import v1_chat, db_utils, core, neo4j_utils, admin, email, neo4j_products

logger.info("FastAPI application initialized and routers included.")

# FastAPI Setup and CORS
api = FastAPI(
    title="AI Enterprise Agent API (v1)",
    description="API for interacting with the LangGraph agent."
)

env_origins = os.getenv("ALLOWED_ORIGINS")

if env_origins:
    ALLOWED_ORIGINS = env_origins.split(",")
else:
    # Default fallback for local dev
    ALLOWED_ORIGINS = [
        "http://localhost:5173", 
        "http://127.0.0.1:5173", 
        "http://localhost:5174", 
        "http://localhost:3000", 
    ]

# Log the allowed origins for debugging
logger.info(f"CORS Allowed Origins: {ALLOWED_ORIGINS}")

api.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS, 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# Register Routers 
api.include_router(core.router)      
api.include_router(v1_chat.router)   
api.include_router(db_utils.router)  
api.include_router(neo4j_utils.router) 
api.include_router(admin.router) 
api.include_router(email.router)
api.include_router(neo4j_products.router)
api.include_router(auth.router)

logger.info("FastAPI startup complete. All routers registered.")