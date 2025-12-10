from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List 
from ..services.email_service import send_order_request_email

router = APIRouter(prefix="/email", tags=["Email"])

# Define a model for a single product item
class ProductItem(BaseModel):
    product_name: str
    quantity: int

# Pydantic model to validate the incoming request data
class OrderRequest(BaseModel):
    # An array of ProductItem
    items: List[ProductItem]
    customer_name: str
    customer_email: str
    customer_phone: str
    customer_address: Optional[str] = None
    notes: Optional[str] = None

@router.post("/order-request")
async def submit_order_request(request: OrderRequest):
    """
    Receives order request data (including multiple items) from the frontend and sends an email.
    """
    print(f"Received order request: {request.dict()}")
    result = send_order_request_email(request.dict())

    if result["status"] == "success":
        return {"message": result["message"]}
    else:
        # Return a 500 error if sending the email failed
        raise HTTPException(status_code=500, detail=result["message"])

print("Email router loaded.")