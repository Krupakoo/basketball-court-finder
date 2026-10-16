import asyncpg
from fastapi import Request
from app.config import DB_CONFIG

async def init_db_pool():
    return await asyncpg.create_pool(**DB_CONFIG)

def get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool