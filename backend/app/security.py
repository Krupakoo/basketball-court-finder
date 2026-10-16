from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from jose import JWTError, jwt
import asyncpg

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from app.database import get_db_pool

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def calculate_rank(xp: int):
    level = (xp // 100) + 1
    if level < 3:
        rank = "Rookie"
    elif level < 6:
        rank = "Streetballer"
    elif level < 10:
        rank = "Court Veteran"
    else:
        rank = "Playmaker Legend"
    return level, rank

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Nieprawidlowy token autoryzacyjny.")
    except JWTError:
        raise HTTPException(status_code=401, detail="Blad weryfikacji tokenu.")

    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT id, username, email, xp_points, COALESCE(is_admin, FALSE) as is_admin FROM users WHERE id = $1;", 
            int(user_id)
        )
        if not user:
            raise HTTPException(status_code=404, detail="Uzytkownik nie istnieje.")
        level, rank = calculate_rank(user["xp_points"])
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "xp_points": user["xp_points"],
            "level": level,
            "rank_title": rank,
            "is_admin": user["is_admin"]
        }