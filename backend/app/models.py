from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr

class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    username_or_email: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    xp_points: int
    level: int
    rank_title: str
    is_admin: bool = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class LeaderboardEntry(BaseModel):
    username: str
    xp_points: int
    level: int
    rank_title: str

class CourtResponse(BaseModel):
    id: int
    name: str
    surface: str
    has_lighting: bool
    hoops_count: int
    backboard_type: Optional[str] = "steel_grid"
    rim_type: Optional[str] = "standard_rigid"
    net_type: Optional[str] = "chain"
    latitude: float
    longitude: float
    distance_meters: Optional[float] = None
    active_players_count: int
    status: str
    images: List[str] = []

class CheckInRequest(BaseModel):
    court_id: int
    user_lat: float
    user_lng: float

class MatchCreateRequest(BaseModel):
    court_id: int
    scheduled_time: str
    max_players: Optional[int] = 6

class MatchResponse(BaseModel):
    id: int
    court_id: int
    creator_username: str
    scheduled_time: str
    max_players: int
    joined_count: int
    is_joined: bool = False

class CourtStatusUpdate(BaseModel):
    status: str