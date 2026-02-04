from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from src.core.security import ALGORITHM, SECRET_KEY
from src.api.db.sessions import get_db
from src.api.db.models import Customer
from src.api.schemas import TokenData

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """
    Validates the token and returns the user.
    Handles both Database Customers and the Hardcoded Admin (ID=0).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("id")
        role: str = payload.get("role")
        
        if email is None:
            raise credentials_exception
            
        token_data = TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    # ADMIN HANDLING
    if user_id == 0 and role == "admin":
        return Customer(id=0, email=email, full_name="System Admin", role="admin")

    # USER HANDLING
    user = db.query(Customer).filter(Customer.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
        
    return user

get_current_customer = get_current_user

def get_current_admin(current_user: Customer = Depends(get_current_user)):
    """
    Checks if the logged-in user has the 'admin' role.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this resource"
        )
    return current_user