from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import os

from src.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from src.api.db.sessions import get_db
from src.api.db.models import Customer
from src.api.schemas import CustomerCreate, CustomerOut, Token, CustomerLogin

router = APIRouter(prefix="/auth", tags=["Authentication"])

ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_HASH = "$2b$12$1Qit6PdOo9fqb.BwnhqYROD82VapqJl4RAOGCqpRMBQqrIs6VPFUq" 

# 1. CUSTOMER REGISTRATION
@router.post("/register", response_model=CustomerOut)
def register_customer(user: CustomerCreate, db: Session = Depends(get_db)):
    db_user = db.query(Customer).filter(Customer.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new customer
    hashed_password = get_password_hash(user.password)
    new_user = Customer(
        email=user.email,
        password_hash=hashed_password,
        full_name=user.full_name,
        role="customer"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# 2. CUSTOMER LOGIN 
@router.post("/login", response_model=Token)
def login_json(user_data: CustomerLogin, db: Session = Depends(get_db)):
    user = db.query(Customer).filter(Customer.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create Token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "id": user.id, "role": user.role},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# 3. ADMIN LOGIN 
@router.post("/token", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    
    if form_data.username == ADMIN_USER:
        if verify_password(form_data.password, ADMIN_HASH):
            access_token = create_access_token(
                data={"sub": "admin", "id": 0, "role": "admin"}
            )
            return {"access_token": access_token, "token_type": "bearer"}

    user = db.query(Customer).filter(Customer.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user.email, "id": user.id, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer"}