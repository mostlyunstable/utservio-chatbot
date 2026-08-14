import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import Service, ServiceArea

logger = logging.getLogger(__name__)


class BusinessKnowledgeService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_services(self, query: str) -> str:
        """
        Searches the real PostgreSQL database for matching services based on the user's query.
        Returns a formatted string of authoritative facts for the LLM context.
        """
        logger.info(f"Looking up business knowledge for query: {query}")

        # Simple wildcard search
        search_term = f"%{query.lower()}%"

        # Include locations
        stmt = (
            select(Service)
            .options(selectinload(Service.areas))
            .where(
                (Service.name.ilike(search_term))
                | (Service.description.ilike(search_term))
            )
            .where(Service.active == 1)
            .limit(5)
        )

        result = await self.db.execute(stmt)
        services = result.scalars().all()

        if not services:
            # Also check if it's a location search
            stmt_loc = (
                select(ServiceArea)
                .options(selectinload(ServiceArea.services))
                .where(ServiceArea.name.ilike(search_term))
                .where(ServiceArea.active == 1)
                .limit(3)
            )
            res_loc = await self.db.execute(stmt_loc)
            areas = res_loc.scalars().all()
            if areas:
                context = "Services available in requested area:\n"
                for a in areas:
                    srvs = [s.name for s in a.services]
                    context += (
                        f"- Location: {a.name}. Services offered: {', '.join(srvs)}\n"
                    )
                return context
            return "No matching services or locations found in the authoritative UTservio database."

        context_lines = []
        for svc in services:
            area_names = [a.name for a in svc.areas] if svc.areas else ["Global"]
            price_info = "Price not listed"
            if svc.price_amount:
                if svc.pricing_type == "starting_from":
                    price_info = f"Starts at {svc.price_amount} {svc.price_currency} {svc.price_unit}"
                elif svc.pricing_type == "fixed":
                    price_info = f"Fixed price {svc.price_amount} {svc.price_currency} {svc.price_unit}"
                else:
                    price_info = (
                        f"{svc.price_amount} {svc.price_currency} {svc.price_unit}"
                    )

            line = f"Service: {svc.name}\nDescription: {svc.description}\nPricing: {price_info}\nAvailable Locations: {', '.join(area_names)}\n(Source: {svc.source_url} | Verified: {svc.last_verified_at})"
            context_lines.append(line)

        return "\n\n".join(context_lines)

    @staticmethod
    async def get_service_areas(db: AsyncSession) -> list[ServiceArea]:
        """Retrieve all supported service areas."""
        stmt = select(ServiceArea)
        result = await db.execute(stmt)
        return list(result.scalars().all())
