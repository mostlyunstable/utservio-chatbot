from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.future import select

from app.commands.sync_website_data import sync_data
from app.db.database import AsyncSessionLocal
from app.db.models import Service, ServiceArea, ServiceAvailability
from app.services.utservio_scraper import UtservioScraper

# ==========================================
# 1. SSRF & URL VALIDATION TESTS
# ==========================================


def test_is_safe_url():
    scraper = UtservioScraper()

    # Safe domains
    assert scraper.is_safe_url("https://utservio.com") is True
    assert scraper.is_safe_url("https://utservio.com/fan-cleaning/perungudi") is True
    assert scraper.is_safe_url("https://www.utservio.com/fan-cleaning") is True

    # Block external domains
    assert scraper.is_safe_url("https://google.com") is False
    assert scraper.is_safe_url("https://evil.com/utservio.com") is False

    # Block internal IPs and localhost
    assert scraper.is_safe_url("http://localhost") is False
    assert scraper.is_safe_url("http://127.0.0.1") is False
    assert scraper.is_safe_url("http://192.168.1.1") is False
    assert scraper.is_safe_url("http://10.0.0.1") is False
    assert scraper.is_safe_url("http://169.254.169.254/latest/meta-data") is False
    assert scraper.is_safe_url("http://[::1]") is False

    # Block unsafe schemes
    assert scraper.is_safe_url("file:///etc/passwd") is False
    assert scraper.is_safe_url("ftp://utservio.com/file") is False


@pytest.mark.asyncio
async def test_fetch_page_safely_redirects_ssrf():
    scraper = UtservioScraper()

    # Mock redirect to internal address
    mock_response_redirect = MagicMock()
    mock_response_redirect.is_redirect = True
    mock_response_redirect.headers = {"location": "http://127.0.0.1/admin"}

    # Patch self.client.stream
    # For httpx.stream, it returns an async context manager
    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response_redirect

    with (
        patch.object(scraper.client, "stream", return_value=mock_stream),
        pytest.raises(ValueError, match="Unsafe or unauthorized URL"),
    ):
        await scraper.fetch_page_safely("https://utservio.com/redirect-evil")


@pytest.mark.asyncio
async def test_fetch_page_safely_oversized_response():
    scraper = UtservioScraper()

    mock_response_large = MagicMock()
    mock_response_large.headers = {"content-length": "10000000"}  # 10MB

    mock_stream = AsyncMock()
    mock_stream.__aenter__.return_value = mock_response_large

    with (
        patch.object(scraper.client, "stream", return_value=mock_stream),
        pytest.raises(ValueError, match="Response size too large"),
    ):
        await scraper.fetch_page_safely("https://utservio.com/large")


# ==========================================
# 2. EXTRACTION STRATEGY & PRICING TESTS
# ==========================================


@pytest.mark.asyncio
async def test_extraction_json_ld():
    scraper = UtservioScraper()

    # HTML with rich JSON-LD FAQPage
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "How much does fan cleaning cost in Perungudi?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Utservio fan cleaning starts at just ₹149 per fan in Perungudi."
              }
            }
          ]
        }
        </script>
      </head>
      <body>
        <p>Some text</p>
      </body>
    </html>
    """

    # Mock safe fetching
    with patch.object(scraper, "fetch_page_safely", return_value=html):
        record = await scraper.scrape_page(
            "https://utservio.com/fan-cleaning/perungudi"
        )
        assert record is not None
        assert record["service_name"] == "Fan Cleaning"
        assert record["location_name"] == "Perungudi"
        assert record["price_amount"] == "149"
        assert record["pricing_type"] == "starting_from"
        assert record["price_unit"] == "per fan"
        assert record["extraction_method"] == "json_ld"


@pytest.mark.asyncio
async def test_extraction_semantic_html_fallback():
    scraper = UtservioScraper()

    # HTML without JSON-LD but with pricing details in text
    html = """
    <html>
      <body>
        <h1>Fan Cleaning in Perungudi</h1>
        <p>Our professional fan cleaning service starts at just ₹149 per fan at your convenience.</p>
      </body>
    </html>
    """

    with patch.object(scraper, "fetch_page_safely", return_value=html):
        record = await scraper.scrape_page(
            "https://utservio.com/fan-cleaning/perungudi"
        )
        assert record is not None
        assert record["price_amount"] == "149"
        assert record["pricing_type"] == "starting_from"
        assert record["price_unit"] == "per fan"
        assert record["extraction_method"] == "semantic_html"


# ==========================================
# 3. IDEMPOTENCY & CHANGE DETECTION DATABASE TESTS
# ==========================================


@pytest.mark.asyncio
async def test_sync_idempotency_and_change_detection():
    # Setup scraper mock sitemap and scrape responses
    sitemap_urls = [
        "https://utservio.com/fan-cleaning/perungudi",
        "https://utservio.com/sweep-and-mop/perungudi",
    ]

    html_fan = """
    <html>
      <body>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "How much does fan cleaning cost?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Fan cleaning starts at ₹149 per fan."
              }
            }
          ]
        }
        </script>
      </body>
    </html>
    """

    html_mop = """
    <html>
      <body>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          "mainEntity": [
            {
              "@type": "Question",
              "name": "How much does sweep and mop cost?",
              "acceptedAnswer": {
                "@type": "Answer",
                "text": "Sweep and mop starts at ₹249 per room."
              }
            }
          ]
        }
        </script>
      </body>
    </html>
    """

    html_content_map = {
        "https://utservio.com/fan-cleaning/perungudi": html_fan,
        "https://utservio.com/sweep-and-mop/perungudi": html_mop,
    }

    # We patch UtservioScraper fetch_sitemap and fetch_page_safely
    with (
        patch.object(UtservioScraper, "fetch_sitemap", return_value=sitemap_urls),
        patch.object(UtservioScraper, "fetch_page_safely") as mock_fetch,
    ):

        async def mock_fetch_side_effect(url, *args, **kwargs):
            return html_content_map.get(url, "")

        mock_fetch.side_effect = mock_fetch_side_effect

        from sqlalchemy import delete

        async with AsyncSessionLocal() as session:
            # Clean DB first
            await session.execute(delete(ServiceAvailability))
            await session.execute(delete(ServiceArea))
            await session.execute(delete(Service))
            await session.commit()

        # Run First Sync
        await sync_data()

        # Count check
        async with AsyncSessionLocal() as session:
            res_srv = await session.execute(select(Service))
            services_after_1 = res_srv.scalars().all()
            assert len(services_after_1) == 2

            fan_service = next(s for s in services_after_1 if s.name == "Fan Cleaning")
            assert fan_service.price_amount == "149"
            assert fan_service.price_unit == "per fan"
            assert fan_service.pricing_type == "starting_from"

            res_area = await session.execute(select(ServiceArea))
            areas_after_1 = res_area.scalars().all()
            assert len(areas_after_1) == 1
            assert areas_after_1[0].name == "Perungudi"

        # Run Second Sync (should be idempotent)
        await sync_data()

        # Confirm no duplicates created
        async with AsyncSessionLocal() as session:
            res_srv = await session.execute(select(Service))
            services_after_2 = res_srv.scalars().all()
            assert len(services_after_2) == 2

            res_area = await session.execute(select(ServiceArea))
            areas_after_2 = res_area.scalars().all()
            assert len(areas_after_2) == 1

        # Change Detection: simulate price change for Fan Cleaning to ₹199
        html_fan_updated = """
         <html>
           <body>
             <script type="application/ld+json">
             {
               "@context": "https://schema.org",
               "@type": "FAQPage",
               "mainEntity": [
                 {
                   "@type": "Question",
                   "name": "How much does fan cleaning cost?",
                   "acceptedAnswer": {
                     "@type": "Answer",
                     "text": "Fan cleaning starts at ₹199 per fan."
                   }
                 }
               ]
             }
             </script>
           </body>
         </html>
         """

        # Update html_content_map to simulate the updated page on the web server
        html_content_map["https://utservio.com/fan-cleaning/perungudi"] = (
            html_fan_updated
        )

        # Run Sync with changes
        with patch("app.commands.sync_website_data.logger.info") as mock_info:
            await sync_data()

            # Verify log contains PRICE_CHANGED
            mock_info.assert_any_call("PRICE_CHANGED: Fan Cleaning")

        # Verify updated price in database
        async with AsyncSessionLocal() as session:
            res_srv = await session.execute(select(Service))
            services_updated = res_srv.scalars().all()
            assert len(services_updated) == 2
            fan_updated = next(s for s in services_updated if s.name == "Fan Cleaning")
            assert fan_updated.price_amount == "199"
