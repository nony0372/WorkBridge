import os
import datetime
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from database import get_db
import models

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY", "secret")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        print("DEBUG: No access_token cookie found")
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/auth/login"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            print("DEBUG: Token payload has no 'sub'")
            raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                                headers={"Location": "/auth/login"})
        user_id = int(str(user_id))
    except (JWTError, ValueError) as e:
        print(f"DEBUG: Token decoding failed: {e}")
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/auth/login"})
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        print(f"DEBUG: User with ID {user_id} not found in DB")
        raise HTTPException(status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                            headers={"Location": "/auth/login"})
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            return None
        return db.query(models.User).filter(models.User.id == user_id).first()
    except JWTError:
        return None


def require_role(role: str):
    def role_checker(current_user: models.User = Depends(get_current_user_from_cookie)):
        if current_user.role != role:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user
    return role_checker
