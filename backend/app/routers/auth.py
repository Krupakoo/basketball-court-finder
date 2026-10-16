from fastapi import APIRouter, Depends, HTTPException
import asyncpg

from app.database import get_db_pool
from app.models import UserRegister, UserLogin, UserResponse, TokenResponse
from app.security import (
    hash_password,
    verify_password,
    create_access_token,
    calculate_rank,
    get_current_user
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister, pool: asyncpg.Pool = Depends(get_db_pool)):
    async with pool.acquire() as conn:
        existing = await conn.fetchrow(
            "SELECT id FROM users WHERE username = $1 OR email = $2;", 
            user_data.username, user_data.email
        )
        if existing:
            raise HTTPException(status_code=400, detail="Uzytkownik o podanym loginie lub adresie e-mail juz istnieje.")

        hashed_pw = hash_password(user_data.password)
        new_user = await conn.fetchrow(
            """
            INSERT INTO users (username, email, password_hash, xp_points, is_admin)
            VALUES ($1, $2, $3, 0, FALSE)
            RETURNING id, username, email, xp_points, is_admin;
            """,
            user_data.username, user_data.email, hashed_pw
        )
        level, rank = calculate_rank(new_user["xp_points"])
        token = create_access_token({"sub": str(new_user["id"])})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_user["id"],
                "username": new_user["username"],
                "email": new_user["email"],
                "xp_points": new_user["xp_points"],
                "level": level,
                "rank_title": rank,
                "is_admin": new_user["is_admin"]
            }
        }

@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, pool: asyncpg.Pool = Depends(get_db_pool)):
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            """
            SELECT id, username, email, password_hash, xp_points, COALESCE(is_admin, FALSE) as is_admin
            FROM users 
            WHERE username = $1 OR email = $1;
            """,
            credentials.username_or_email
        )
        if not user or not verify_password(credentials.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Nieprawidlowy login lub haslo.")

        level, rank = calculate_rank(user["xp_points"])
        token = create_access_token({"sub": str(user["id"])})
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "xp_points": user["xp_points"],
                "level": level,
                "rank_title": rank,
                "is_admin": user["is_admin"]
            }
        }

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    return current_user