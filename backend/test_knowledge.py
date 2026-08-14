import asyncio

from app.db.database import AsyncSessionLocal
from app.services.knowledge import BusinessKnowledgeService


async def test():
    async with AsyncSessionLocal() as db:
        bk = BusinessKnowledgeService(db)
        res = await bk.search_services("fan cleaning")
        print("--- KNOWLEDGE SEARCH FOR 'fan cleaning' ---")
        print(res)

        res = await bk.search_services("Perungudi")
        print("--- KNOWLEDGE SEARCH FOR 'Perungudi' ---")
        print(res)


if __name__ == "__main__":
    asyncio.run(test())
