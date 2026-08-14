import asyncio

from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.db.models import Service, ServiceArea, ServiceAvailability


async def count():
    async with AsyncSessionLocal() as session:
        srvs = (await session.execute(select(Service))).scalars().all()
        areas = (await session.execute(select(ServiceArea))).scalars().all()
        links = (await session.execute(select(ServiceAvailability))).scalars().all()

        print(f"Total Services: {len(srvs)}")
        print(f"Total Service Areas: {len(areas)}")
        print(f"Total Availabilities: {len(links)}")

        for s in srvs[:3]:
            print(
                f"- Service: {s.name}, Price: {s.price_amount} {s.price_currency} {s.price_unit}, Pricing Type: {s.pricing_type}, Source: {s.source_url}, Extraction: {s.extraction_method}"
            )

        for a in areas[:3]:
            print(f"- Area: {a.name}, Source: {a.source_url}")


if __name__ == "__main__":
    asyncio.run(count())
