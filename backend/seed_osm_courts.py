import asyncio
import asyncpg

DB_CONFIG = {
    "user": "basket_user",
    "password": "basket_password123",
    "database": "basketball_db",
    "host": "localhost",
    "port": 5432
}

MISSING_COURTS = [
    {
        "name": "Boisko Koszykarskie Jadowniki (obok stadionu)",
        "surface": "asphalt",
        "hoops_count": 2,
        "has_lighting": False,
        "lat": 49.9610,
        "lng": 20.6420,
    },
    {
        "name": "Streetball Park Wola Dębińska",
        "surface": "concrete",
        "hoops_count": 1,
        "has_lighting": False,
        "lat": 49.9821,
        "lng": 20.7350,
    },
    {
        "name": "Boisko do koszykówki Okocim",
        "surface": "asphalt",
        "hoops_count": 2,
        "has_lighting": False,
        "lat": 49.9480,
        "lng": 20.5980,
    }
]

async def seed_remaining():
    conn = await asyncpg.connect(**DB_CONFIG)

    # Pobieramy dopuszczalne wartości dla typów nawierzchni
    rows = await conn.fetch("""
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'surface_type_enum';
    """)
    valid_surfaces = [r['enumlabel'] for r in rows]
    fallback_surface = valid_surfaces[0] if valid_surfaces else "tartan"

    query = """
        INSERT INTO courts (
            name, surface, hoops_count, has_lighting, 
            backboard_type, rim_type, net_type, 
            status, location
        )
        VALUES (
            $1, $2, $3, $4, 
            'steel_grid', 'standard_rigid', 'chain', 
            'verified', ST_SetSRID(ST_MakePoint($5, $6), 4326)::geography
        )
    """

    inserted = 0
    try:
        for c in MISSING_COURTS:
            surf = c["surface"] if c["surface"] in valid_surfaces else fallback_surface
            try:
                await conn.execute(
                    query, 
                    c["name"], 
                    surf, 
                    c["hoops_count"], 
                    c["has_lighting"], 
                    c["lng"], 
                    c["lat"]
                )
                inserted += 1
            except Exception as e:
                print(f"Błąd dla {c['name']}: {e}")

        print(f"Dodano pozostałe {inserted} boiska!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_remaining())