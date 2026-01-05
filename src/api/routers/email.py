from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List 
from ..services.email_service import send_order_request_email

router = APIRouter(prefix="/email", tags=["Email"])

# Define a model for a single product item
class ProductItem(BaseModel):
    product_name: str
    quantity: int

# Model to validate the incoming request data
class OrderRequest(BaseModel):
    # An array of ProductItem
    items: List[ProductItem]
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: Optional[str] = None
    notes: Optional[str] = None

@router.post("/order-request")
async def submit_order_request(request: OrderRequest, background_tasks: BackgroundTasks):
    """
    Receives order request data (including multiple items) from the frontend and sends an email in the background to prevent blocking
    """
    
    print(f"Received order request for: {request.customer_name}")

    background_tasks.add_task(send_order_request_email, request.dict())

    return {"message": "Order request received. Processing emails in background."}

print("Email router loaded.")