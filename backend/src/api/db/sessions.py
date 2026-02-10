import os
import urllib.parse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Get DB credentials from .env
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "agent_db")

# 1. URL Encode the password (safety for special characters)
encoded_password = urllib.parse.quote_plus(POSTGRES_PASSWORD)

SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{encoded_password}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# 2. Configure Connection Arguments
connect_args = {}

# If we are connecting to Supabase (or any remote SSL DB), enforce SSL
if "supabase" in POSTGRES_HOST or "aws" in POSTGRES_HOST:
    connect_args = {"sslmode": "require"}

# Create the Database Engine
# pool_pre_ping=True helps prevent "server closed the connection unexpectedly" errors common in cloud DBs
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True 
)

# Create a Session Factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency for FastAPI Routers
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()