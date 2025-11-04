from fastapi import APIRouter

# Defines a router instance
router = APIRouter(tags=["Global/System"])

@router.get("/")
async def root():
    """Root endpoint for a general check."""
    return {"message": "AI Enterprise Agent API is running! Access docs at /docs or use /health."}

@router.get("/health")
async def health_check():
    """Health check endpoint, essential for deployment and monitoring."""
    return {"status": "ok", "service": "ai-enterprise-agent"}