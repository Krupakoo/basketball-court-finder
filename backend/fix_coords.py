import asyncio
import asyncpg

async def fix():
    conn = await asyncpg.connect("postgresql://basket_user:basket_password123@localhost:5432/basketball_db")
    await conn.execute("""
        UPDATE courts 
        SET location = ST_SetSRID(ST_MakePoint(20.6125, 49.9765), 4326)::geography 
        WHERE name LIKE '%SP nr 2%' OR name LIKE '%Szko%';
    """)
    print("Wspolrzedne zaktualizowane pomyslnie!")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(fix())