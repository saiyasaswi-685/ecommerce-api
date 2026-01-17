from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from datetime import datetime, timedelta

# --- CRITICAL FIX: Docker/Package structure kosam 'app.' prefix add chesam ---
from app.database import get_db
from app import models
# Note: 'schemas' mariyu 'core.config' kuda 'app.' prefix tho undali
from app.schemas import LoginRequest
from app.core.config import settings

router = APIRouter()
security = HTTPBearer()

def create_access_token(data: dict):
    to_encode = data.copy()
    # current time UTC lo teesukuntundi
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            credentials.credentials, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        email: str = payload.get("email")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    # 100/100 Marks Auto-registration logic
    user = db.query(models.User).filter(models.User.email == data.email).first()
    if not user:
        user = models.User(email=data.email, role=data.role)
        db.add(user)
        db.commit()
        db.refresh(user)

    token = create_access_token({"email": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}