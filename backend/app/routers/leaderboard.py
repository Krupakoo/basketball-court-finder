from typing import List
from fastapi import APIRouter, Depends, Query
import asyncpg

from app.database import get_db_pool
from app.models import LeaderboardEntry
from app.security import calculate_rank

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])

@router.get("", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    async with pool.acquire() as conn:
        records = await conn.fetch(
            """
            SELECT username, xp_points
            FROM users
            WHERE COALESCE(is_admin, FALSE) = FALSE
            ORDER BY xp_points DESC, id ASC
            LIMIT $1;
            """,
            limit
        )
        results = []
        for r in records:
            lvl, rank = calculate_rank(r["xp_points"])
            results.append({
                "username": r["username"],
                "xp_points": r["xp_points"],
                "level": lvl,
                "rank_title": rank
            })
        return results