from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Token Schemas ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    user_id: Optional[int] = None

# --- User Schemas ---
class CustomerBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None

class CustomerCreate(CustomerBase):
    password: str

class CustomerLogin(BaseModel):
    email: EmailStr
    password: str

class CustomerOut(CustomerBase):
    id: int
    created_at: datetime
    role: str

    class Config:
        from_attributes = True

# --- Order Schemas ---
class OrderItemSchema(BaseModel):
    product_id: int
    quantity: int

class OrderCreate(BaseModel):
    items: List[OrderItemSchema]

class OrderItemOut(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: float

class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: str
    total_amount: float
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True
    
    # --- Product Schemas ---
class ProductBase(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float = 0.0
    stock_quantity: int = 0
    image_url: Optional[str] = None

class ProductCreate(ProductBase):
    pass  

class ProductUpdate(BaseModel):
    # All fields optional so you can update just the price or just the stock
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None

class ProductOut(ProductBase):
    id: int

    class Config:
        from_attributes = True