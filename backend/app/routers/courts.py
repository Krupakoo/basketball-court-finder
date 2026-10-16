import os
import shutil
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from jose import JWTError, jwt
import asyncpg
import httpx

from app.config import UPLOAD_DIR, SURFACE_MAP, BACKBOARD_MAP, RIM_MAP, NET_MAP, SECRET_KEY, ALGORITHM
from app.database import get_db_pool
from app.models import CourtResponse, CourtStatusUpdate, CheckInRequest, MatchResponse
from app.security import get_current_user, oauth2_scheme_optional

router = APIRouter(tags=["courts"])

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
]


# Pobieranie boisk w zadanym promieniu (domyślnie 5 km)
@router.get("/api/courts/nearby", response_model=List[CourtResponse])
async def get_nearby_courts(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_meters: int = Query(5000),
    has_lighting: Optional[bool] = Query(None),
    rim_type: Optional[str] = Query(None),
    min_hoops: Optional[int] = Query(None),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    conditions = ["ST_DWithin(c.location, ST_MakePoint($1, $2)::geography, $3)"]
    params = [lng, lat, radius_meters]

    if has_lighting is True:
        conditions.append("c.has_lighting = TRUE")
    if rim_type:
        mapped_rim = RIM_MAP.get(rim_type.lower(), rim_type)
        params.append(mapped_rim)
        conditions.append(f"c.rim_type = ${len(params)}")
    if min_hoops:
        params.append(min_hoops)
        conditions.append(f"c.hoops_count >= ${len(params)}")

    where_clause = " AND ".join(conditions)

    query = f"""
    SELECT 
        c.id, 
        c.name, 
        c.surface,
        c.has_lighting,
        c.hoops_count,
        COALESCE(c.backboard_type, 'steel_grid') AS backboard_type,
        COALESCE(c.rim_type, 'standard_rigid') AS rim_type,
        COALESCE(c.net_type, 'chain') AS net_type,
        c.status,
        ST_Y(c.location::geometry) AS latitude,
        ST_X(c.location::geometry) AS longitude,
        ROUND(ST_Distance(c.location, ST_MakePoint($1, $2)::geography)) AS distance_meters,
        COUNT(DISTINCT ci.id) FILTER (WHERE ci.is_active = TRUE AND ci.expires_at > CURRENT_TIMESTAMP) AS active_players_count,
        COALESCE(
            ARRAY_AGG(ci_img.image_url) FILTER (WHERE ci_img.image_url IS NOT NULL), 
            '{{}}'
        ) AS images
    FROM courts c
    LEFT JOIN check_ins ci ON c.id = ci.court_id
    LEFT JOIN court_images ci_img ON c.id = ci_img.court_id
    WHERE {where_clause}
    GROUP BY c.id
    ORDER BY distance_meters ASC;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query, *params)
        return [dict(r) for r in records]


# Zgłaszanie nowego boiska wraz ze zdjęciami weryfikacyjnymi (dzikie boiska / brakujące)
@router.post("/api/courts", status_code=status.HTTP_201_CREATED)
async def create_court(
    name: str = Form(...),
    surface: str = Form(...),
    hoops_count: int = Form(...),
    has_lighting: bool = Form(False),
    backboard_type: str = Form("steel_grid"),
    rim_type: str = Form("standard_rigid"),
    net_type: str = Form("chain"),
    latitude: float = Form(...),
    longitude: float = Form(...),
    images: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    if not images:
        raise HTTPException(status_code=400, detail="Wymagane jest przynajmniej jedno zdjecie weryfikacyjne.")

    db_surface = SURFACE_MAP.get(surface.lower(), "asphalt")
    db_backboard = BACKBOARD_MAP.get(backboard_type.lower(), "steel_grid")
    db_rim = RIM_MAP.get(rim_type.lower(), "standard_rigid")
    db_net = NET_MAP.get(net_type.lower(), "chain")

    async with pool.acquire() as conn:
        async with conn.transaction():
            court_row = await conn.fetchrow(
                """
                INSERT INTO courts (
                    name, surface, hoops_count, has_lighting, 
                    backboard_type, rim_type, net_type, 
                    location, status
                )
                VALUES (
                    $1, $2, $3, $4, 
                    $5, $6, $7, 
                    ST_SetSRID(ST_MakePoint($8, $9), 4326), 'pending'
                )
                RETURNING id;
                """,
                name, db_surface, hoops_count, has_lighting,
                db_backboard, db_rim, db_net,
                longitude, latitude
            )
            court_id = court_row["id"]

            for img in images:
                file_ext = os.path.splitext(img.filename)[1].lower()
                if file_ext not in [".jpg", ".jpeg", ".png", ".webp"]:
                    continue
                
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                file_path = os.path.join(UPLOAD_DIR, unique_filename)
                
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(img.file, buffer)

                relative_url = f"/uploads/{unique_filename}"
                await conn.execute(
                    """
                    INSERT INTO court_images (court_id, image_url, uploaded_by)
                    VALUES ($1, $2, $3);
                    """,
                    court_id, relative_url, current_user["id"]
                )

    return {
        "message": "Boisko zostalo zgloszone i oczekuje na weryfikacje zdjec.",
        "court_id": court_id,
        "status": "pending"
    }


# Weryfikacja i moderacja zgłoszeń boisk (tylko administrator)
@router.patch("/api/admin/courts/{court_id}/status")
async def update_court_status(
    court_id: int,
    payload: CourtStatusUpdate,
    current_user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Brak uprawnien administratora.")

    if payload.status not in ["verified", "rejected"]:
        raise HTTPException(status_code=400, detail="Nieprawidlowy status obiektu.")

    async with pool.acquire() as conn:
        if payload.status == "rejected":
            await conn.execute("DELETE FROM courts WHERE id = $1;", court_id)
            return {"message": "Zgloszenie zostalo odrzucone, a obiekt usuniety."}
        else:
            await conn.execute("UPDATE courts SET status = 'verified' WHERE id = $1;", court_id)
            return {"message": "Boisko zostalo pomyslnie zweryfikowane."}


# Check-in (weryfikacja geofencingu 75 m i przyznanie 25 XP)
@router.post("/api/check-in")
async def check_in(
    req: CheckInRequest, 
    current_user: dict = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    user_id = current_user["id"]
    async with pool.acquire() as conn:
        distance = await conn.fetchval(
            """
            SELECT ST_Distance(location, ST_MakePoint($1, $2)::geography)
            FROM courts WHERE id = $3;
            """,
            req.user_lng, req.user_lat, req.court_id
        )
        if distance is None:
            raise HTTPException(status_code=404, detail="Boisko nie istnieje.")

        if distance > 75.0:
            raise HTTPException(
                status_code=400,
                detail=f"Zbyt duza odleglosc ({int(distance)} m). Wymagana odleglosc wynosi maksymalnie 75 m."
            )

        await conn.execute(
            """
            UPDATE check_ins SET is_active = FALSE 
            WHERE user_id = $1 AND is_active = TRUE;
            """,
            user_id
        )

        expires = datetime.now(timezone.utc) + timedelta(hours=2)
        await conn.execute(
            """
            INSERT INTO check_ins (user_id, court_id, expires_at, is_active)
            VALUES ($1, $2, $3, TRUE);
            """,
            user_id, req.court_id, expires
        )

        if not current_user.get("is_admin"):
            await conn.execute(
                "UPDATE users SET xp_points = xp_points + 25 WHERE id = $1;",
                user_id
            )

        return {"message": "Zameldowano pomyslnie. Przyznano 25 punktow XP.", "distance_meters": round(distance)}


# Pobieranie zaplanowanych meczów dla danego boiska
@router.get("/api/courts/{court_id}/matches", response_model=List[MatchResponse])
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


# Automatyczne wykrywanie boisk (OpenStreetMap + PostGIS centroidy)
@router.post("/api/courts/auto-discover")
async def auto_discover_courts(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_meters: int = Query(6000),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    query = f"""
    [out:json][timeout:25];
    (
      node["leisure"="pitch"]["sport"~"basketball|multi"](around:{radius_meters},{lat},{lng});
      way["leisure"="pitch"]["sport"~"basketball|multi"](around:{radius_meters},{lat},{lng});
    );
    out center tags;
    """
    headers = {"User-Agent": "BasketballCourtFinder/1.0 (academic research)"}
    elements = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for mirror in OVERPASS_MIRRORS:
            try:
                resp = await client.post(mirror, data={"data": query}, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    elements = data.get("elements", [])
                    if elements:
                        break
            except Exception:
                continue

    if not elements:
        return {"message": "Nie znaleziono nowych obiektów w tym rejonie.", "added": 0}

    insert_query = """
    INSERT INTO courts (
        name, surface, hoops_count, has_lighting, 
        backboard_type, rim_type, net_type, 
        status, location
    )
    SELECT 
        $1, $2, $3, $4, 
        'steel_grid', 'standard_rigid', 'chain', 
        'verified', ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography
    WHERE NOT EXISTS (
        SELECT 1 FROM courts 
        WHERE ST_DWithin(location, ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography, 40)
    );
    """

    added_count = 0
    async with pool.acquire() as conn:
        for el in elements:
            coords = el.get("center") if el.get("type") == "way" else el
            c_lat = coords.get("lat")
            c_lng = coords.get("lon")
            if not c_lat or not c_lng:
                continue

            tags = el.get("tags", {})
            name = tags.get("name") or tags.get("description") or f"Boisko {tags.get('sport', 'wielofunkcyjne')}"
            
            raw_surface = tags.get("surface", "").lower()
            if any(s in raw_surface for s in ["tartan", "rubber", "polyurethane"]):
                db_surface = SURFACE_MAP.get("tartan", "tartan")
            elif "concrete" in raw_surface:
                db_surface = SURFACE_MAP.get("beton", "concrete")
            else:
                db_surface = SURFACE_MAP.get("asfalt", "asphalt")

            has_lighting = tags.get("lit") in ["yes", "24/7", "true"]

            res = await conn.execute(insert_query, name, db_surface, 2, has_lighting, c_lng, c_lat)
            if "INSERT 0 1" in res:
                added_count += 1

    return {
        "message": f"Wykryto i dodano {added_count} nowych boisk do bazy.",
        "added": added_count
    }
