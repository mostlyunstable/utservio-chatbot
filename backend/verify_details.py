import asyncio

from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.db.models import Service


async def verify():
    async with AsyncSessionLocal() as session:
        stmt = (
            select(Service)
            .options(selectinload(Service.areas))
            .where(Service.name == "Fan Cleaning")
        )
        res = await session.execute(stmt)
        svc = res.scalars().first()
        if not svc:
            print("Fan Cleaning not found")
            return

        print("--- PROVENANCE AND SEMANTICS AUDIT ---")
        print(f"Service Name: {svc.name}")
        print(f"Price Amount: {svc.price_amount}")
        print(f"Price Currency: {svc.price_currency}")
        print(f"Pricing Type: {svc.pricing_type}")
        print(f"Price Unit: {svc.price_unit}")
        print(f"Source URL: {svc.source_url}")
        print(f"Source Domain: {svc.source_domain}")
        print(f"Retrieved At: {svc.retrieved_at}")
        print(f"Verified At: {svc.last_verified_at}")
        print(f"Extraction Method: {svc.extraction_method}")
        print(f"Available Areas: {[a.name for a in svc.areas]}")


if __name__ == "__main__":
    asyncio.run(verify())
