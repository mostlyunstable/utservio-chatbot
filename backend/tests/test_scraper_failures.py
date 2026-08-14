from unittest.mock import patch

import pytest
from sqlalchemy.future import select

from app.commands.sync_website_data import sync_data
from app.db.database import AsyncSessionLocal
from app.db.models import Service, ServiceArea, ServiceAvailability
from app.services.utservio_scraper import UtservioScraper


@pytest.mark.asyncio
async def test_scraper_partial_failures_and_rollback():
    # Setup scraper mock sitemap: 3 pages
    sitemap_urls = [
        "https://utservio.com/fan-cleaning/perungudi",
        "https://utservio.com/sweep-and-mop/perungudi",
        "https://utservio.com/bathroom-cleaning/perungudi",
    ]

    html_fan = '<html><body><script type=\'application/ld+json\'>{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "Price?", "acceptedAnswer": {"@type": "Answer", "text": "Fan cleaning starts at ₹149 per fan"}}]}</script></body></html>'
    html_bathroom = '<html><body><script type=\'application/ld+json\'>{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [{"@type": "Question", "name": "Price?", "acceptedAnswer": {"@type": "Answer", "text": "Bathroom cleaning starts at ₹349"}}]}</script></body></html>'

    # We mock fetch_sitemap and fetch_page_safely
    with (
        patch.object(UtservioScraper, "fetch_sitemap", return_value=sitemap_urls),
        patch.object(UtservioScraper, "fetch_page_safely") as mock_fetch,
    ):

        async def mock_fetch_side_effect(url, *args, **kwargs):
            if "fan-cleaning" in url:
                return html_fan
            elif "sweep-and-mop" in url:
                # Page 2 fails (e.g. timeout or exception)
                raise ValueError("Simulated network timeout/HTTP error")
            elif "bathroom-cleaning" in url:
                return html_bathroom
            return ""

        mock_fetch.side_effect = mock_fetch_side_effect

        # Clean database
        from sqlalchemy import delete

        async with AsyncSessionLocal() as session:
            await session.execute(delete(ServiceAvailability))
            await session.execute(delete(ServiceArea))
            await session.execute(delete(Service))
            await session.commit()

        # Run sync. Even though sweep-and-mop fails, sync_data should log it and continue
        await sync_data()

        # Verify database contents
        async with AsyncSessionLocal() as session:
            # We should have "Fan Cleaning" and "Bathroom Cleaning" in DB
            res_srv = await session.execute(select(Service))
            services = res_srv.scalars().all()

            names = [s.name for s in services]
            assert "Fan Cleaning" in names
            assert "Bathroom Cleaning" in names
            assert "Sweep And Mop" not in names

            # We should still have Perungudi service area (created by page 1)
            res_area = await session.execute(select(ServiceArea))
            areas = res_area.scalars().all()
            assert len(areas) == 1
            assert areas[0].name == "Perungudi"

            # Clean rollback verification: make sure the session/transaction is valid for subsequent ops
            # and page 2 did not affect page 3 commit
            bathroom_service = next(
                s for s in services if s.name == "Bathroom Cleaning"
            )
            assert bathroom_service.price_amount == "349"
