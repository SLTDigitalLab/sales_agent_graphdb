from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict
import os
from .api import auth

from .api.services.chat_service import chat_histories 

# Importing Routers
from .api.routers import v1_chat, db_utils, core, neo4j_utils, admin, email,neo4j_products

print("FastAPI application initialized and routers included.")

# FastAPI Setup and CORS
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

# Serve admin dashboard
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 
admin_dashboard_path = os.path.join(project_root, 'admin-dashboard')
api.mount("/admin-ui", StaticFiles(directory=admin_dashboard_path, html=True), name="admin-ui")

# Register Routers 
api.include_router(core.router)      
api.include_router(v1_chat.router)   
api.include_router(db_utils.router)  
api.include_router(neo4j_utils.router) 
api.include_router(admin.router) 
api.include_router(email.router)
api.include_router(neo4j_products.router)
api.include_router(auth.router)

print("FastAPI application initialized and routers included.")