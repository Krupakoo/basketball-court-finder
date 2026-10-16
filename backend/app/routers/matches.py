from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
import asyncpg

from app.config import SECRET_KEY, ALGORITHM
from app.database import get_db_pool
from app.models import MatchResponse, MatchCreateRequest
from app.security import get_current_user, oauth2_scheme_optional

router = APIRouter(prefix="/api/matches", tags=["matches"])

@router.get("/court/{court_id}", response_model=List[MatchResponse])
@router.get("/courts/{court_id}/matches", response_model=List[MatchResponse])
async def get_court_matches(
    court_id: int, 
    token: Optional[str] = Depends(oauth2_scheme_optional),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    current_user_id = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            current_user_id = int(payload.get("sub"))
        except JWTError:
            pass

    query = """
    SELECT 
        m.id, 
        m.court_id, 
        u.username AS creator_username,
        to_char(m.scheduled_time, 'YYYY-MM-DD HH24:MI') AS scheduled_time,
        m.max_players,
        COUNT(mp.user_id)::int AS joined_count,
        COALESCE(BOOL_OR(mp.user_id = $2), FALSE) AS is_joined
    FROM matches m
    JOIN users u ON m.created_by_user_id = u.id
    LEFT JOIN match_participants mp ON m.id = mp.match_id
    WHERE m.court_id = $1 AND m.scheduled_time > CURRENT_TIMESTAMP
    GROUP BY m.id, u.username
    ORDER BY m.scheduled_time ASC;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query, court_id, current_user_id)
        results = []
        for r in records:
            d = dict(r)
            d["is_joined"] = bool(d["is_joined"])
            results.append(d)
        return results

# Zachowujemy też pierwotny alias ścieżki dla zgodności wstecznej z frontem
@router.get("/../courts/{court_id}/matches", response_model=List[MatchResponse], include_in_schema=False)
async def get_court_matches_alias(
    court_id: int, 
    token: Optional[str] = Depends(oauth2_scheme_optional),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    return await get_court_matches(court_id, token, pool)

@router.post("")
async def create_match(
    req: MatchCreateRequest, 
    current_user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    user_id = current_user["id"]
    try:
        parsed_time = datetime.fromisoformat(req.scheduled_time)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Nieprawidlowy format daty: {str(e)}")

    async with pool.acquire() as conn:
        async with conn.transaction():
            match_id = await conn.fetchval(
                """
                INSERT INTO matches (court_id, created_by_user_id, scheduled_time, max_players, status)
                VALUES ($1, $2, $3, $4, 'open')
                RETURNING id;
                """,
                req.court_id, user_id, parsed_time, req.max_players
            )
            await conn.execute(
                """
                INSERT INTO match_participants (match_id, user_id) 
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING;
                """,
                match_id, user_id
            )
        return {"message": "Wydarzenie zostalo utworzone.", "match_id": match_id}

@router.post("/{match_id}/join")
async def join_match(
    match_id: int, 
    current_user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    user_id = current_user["id"]
    async with pool.acquire() as conn:
        match = await conn.fetchrow(
            """
            SELECT m.max_players, COUNT(mp.user_id)::int AS joined_count
            FROM matches m
            LEFT JOIN match_participants mp ON m.id = mp.match_id
            WHERE m.id = $1
            GROUP BY m.id;
            """,
            match_id
        )
        if not match:
            raise HTTPException(status_code=404, detail="Mecz nie istnieje.")

        if match["joined_count"] >= match["max_players"]:
            raise HTTPException(status_code=400, detail="Brak wolnych miejsc w skladzie.")

        exists = await conn.fetchrow(
            "SELECT 1 FROM match_participants WHERE match_id = $1 AND user_id = $2;",
            match_id, user_id
        )
        if exists:
            raise HTTPException(status_code=400, detail="Uzytkownik jest juz zapisany do tego wydarzenia.")

        await conn.execute(
            """
            INSERT INTO match_participants (match_id, user_id) 
            VALUES ($1, $2);
            """,
            match_id, user_id
        )
        return {"message": "Dolaczono do skladu."}

@router.delete("/{match_id}/leave")
async def leave_match(
    match_id: int, 
    current_user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    user_id = current_user["id"]
    async with pool.acquire() as conn:
        deleted = await conn.execute(
            "DELETE FROM match_participants WHERE match_id = $1 AND user_id = $2;",
            match_id, user_id
        )
        if deleted == "DELETE 0":
            raise HTTPException(status_code=400, detail="Nie jestes zapisany do tego meczu.")
        return {"message": "Opuszczono sklad meczu."}