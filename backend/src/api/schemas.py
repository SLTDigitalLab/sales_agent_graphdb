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
    product_id: Optional[int] = None
    sku: Optional[str] = None
    quantity: int
    unit_price: float

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    customer_id: int
    status: str
    total_amount: float
    created_at: datetime
    items: List[OrderItemOut]

    class Config:
        from_attributes = True

class OrderStatusUpdate(BaseModel):
    status: str

# --- Product Schemas ---

# 1. Base contains fields common to everything EXCEPT sku (since we generate it later)
class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    price: float = 0.0
    stock_quantity: int = 0
    image_url: Optional[str] = None
    product_url: Optional[str] = None

# 2. Creation schema doesn't need anything extra
class ProductCreate(ProductBase):
    pass  

# 3. Update schema remains all optional
class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    stock_quantity: Optional[int] = None
    image_url: Optional[str] = None
    product_url: Optional[str] = None

# 4. Out schema ADDS the sku and id because the database will return them
class ProductOut(ProductBase):
    id: int
    sku: str  # Add sku here so the frontend still receives it!

    class Config:
        from_attributes = True