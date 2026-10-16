from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import UPLOAD_DIR
from app.database import init_db_pool
from app.routers import auth, courts, matches, leaderboard

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await init_db_pool()
    yield
    await app.state.pool.close()

app = FastAPI(
    title="Basketball Court Finder API", 
    version="1.0.0", 
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(auth.router)
app.include_router(courts.router)
app.include_router(matches.router)
app.include_router(leaderboard.router)