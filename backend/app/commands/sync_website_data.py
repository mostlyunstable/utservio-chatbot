import asyncio
import logging

from sqlalchemy.future import select

from app.db.database import AsyncSessionLocal
from app.db.models import Service, ServiceArea, ServiceAvailability
from app.services.utservio_scraper import UtservioScraper

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def sync_data():
    scraper = UtservioScraper()
    logger.info("Fetching sitemap...")
    urls = await scraper.fetch_sitemap()
    if not urls:
        logger.error("No URLs found in sitemap.")
        await scraper.close()
        return

    logger.info(f"Discovered {len(urls)} URLs. Processing...")

    for url in urls:
        # Each URL is processed in its own database session and transaction
        # to ensure that one failure does not impact other URLs or leave the transaction in a broken state.
        async with AsyncSessionLocal() as session:
            try:
                record = await scraper.scrape_page(url)
                if not record:
                    continue

                # Idempotent Upsert for Service
                stmt = select(Service).where(Service.name == record["service_name"])
                result = await session.execute(stmt)
                service = result.scalars().first()

                is_new_service = False
                if not service:
                    service = Service(
                        name=record["service_name"], category=record["category"]
                    )
                    session.add(service)
                    await session.flush()  # obtain service.id
                    is_new_service = True
                    logger.info(f"SERVICE_ADDED: {service.name}")

                # Change detection checks
                price_changed = False
                content_changed = False

                if not is_new_service:
                    if service.description != record["description"]:
                        content_changed = True
                    if record["price_amount"] and (
                        service.price_amount != record["price_amount"]
                        or service.price_currency != record["price_currency"]
                        or service.pricing_type != record["pricing_type"]
                        or service.price_unit != record["price_unit"]
                    ):
                        price_changed = True

                # Update Service attributes
                service.description = record["description"]
                if record["price_amount"]:
                    service.price_amount = record["price_amount"]
                    service.price_currency = record["price_currency"]
                    service.pricing_type = record["pricing_type"]
                    service.price_unit = record["price_unit"]

                service.source_url = record["source_url"]
                service.source_domain = record["source_domain"]
                service.retrieved_at = record["retrieved_at"]
                service.last_verified_at = record["retrieved_at"]
                service.extraction_method = record["extraction_method"]
                service.active = 1

                if not is_new_service:
                    if price_changed:
                        logger.info(f"PRICE_CHANGED: {service.name}")
                    if content_changed:
                        logger.info(f"CONTENT_CHANGED: {service.name}")
                    if not price_changed and not content_changed:
                        logger.info(
                            f"SERVICE_UPDATED (No semantic changes): {service.name}"
                        )

                # Handle ServiceArea
                if record["location_name"]:
                    stmt_area = select(ServiceArea).where(
                        ServiceArea.name == record["location_name"]
                    )
                    result_area = await session.execute(stmt_area)
                    area = result_area.scalars().first()

                    if not area:
                        area = ServiceArea(
                            name=record["location_name"],
                            active=1,
                            source_url=record["source_url"],
                            source_domain=record["source_domain"],
                            retrieved_at=record["retrieved_at"],
                            last_verified_at=record["retrieved_at"],
                            extraction_method=record["extraction_method"],
                        )
                        session.add(area)
                        await session.flush()
                        logger.info(f"SERVICE_AREA_ADDED: {area.name}")
                    else:
                        # Log area update
                        area.last_verified_at = record["retrieved_at"]
                        logger.info(f"SERVICE_AREA_UPDATED: {area.name}")

                    # Check mapping
                    stmt_link = select(ServiceAvailability).where(
                        ServiceAvailability.service_id == service.id,
                        ServiceAvailability.service_area_id == area.id,
                    )
                    result_link = await session.execute(stmt_link)
                    link = result_link.scalars().first()

                    if not link:
                        session.add(
                            ServiceAvailability(
                                service_id=service.id, service_area_id=area.id
                            )
                        )

                await session.commit()
            except Exception as e:  # noqa: BLE001
                logger.error(
                    f"Error processing URL {url}: {e}. Rolling back transaction."
                )
                await session.rollback()

            await asyncio.sleep(0.5)  # Rate limiting delay

    await scraper.close()
    logger.info("Synchronization complete.")


if __name__ == "__main__":
    asyncio.run(sync_data())
