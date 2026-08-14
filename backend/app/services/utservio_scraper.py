import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

import ipaddress
import socket
from urllib.parse import urljoin


class UtservioScraper:
    def __init__(self, base_url="https://utservio.com"):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.client = httpx.AsyncClient(timeout=10.0)

    def is_safe_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # Restrict domain strictly to utservio.com or www.utservio.com
            if hostname not in ("utservio.com", "www.utservio.com"):
                return False

            # Reject raw IP hostnames
            try:
                ipaddress.ip_address(hostname)
                return False
            except ValueError:
                pass

            # Resolve DNS and check for private / internal IP ranges
            addr_info = socket.getaddrinfo(hostname, None)
            for family, _, _, _, sockaddr in addr_info:
                ip = sockaddr[0]
                ip_obj = ipaddress.ip_address(ip)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                ):
                    return False
            return True
        except Exception:  # noqa: BLE001
            return False

    async def fetch_page_safely(
        self, url: str, max_redirects=3, max_size=5 * 1024 * 1024
    ) -> str:
        redirects = 0
        current_url = url
        while redirects <= max_redirects:
            if not self.is_safe_url(current_url):
                raise ValueError(f"Unsafe or unauthorized URL: {current_url}")

            # Using streaming to validate content size before reading
            async with self.client.stream(
                "GET", current_url, follow_redirects=False
            ) as response:
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > max_size:
                    raise ValueError(f"Response size too large: {content_length} bytes")

                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise ValueError("Redirect header missing Location")
                    current_url = urljoin(current_url, location)
                    redirects += 1
                    continue

                response.raise_for_status()

                body = bytearray()
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    body.extend(chunk)
                    if len(body) > max_size:
                        raise ValueError("Response body exceeded size limit")

                return body.decode(response.encoding or "utf-8", errors="ignore")
        raise ValueError("Too many redirects")

    async def fetch_sitemap(self):
        url = f"{self.base_url}/sitemap.xml"
        try:
            html_content = await self.fetch_page_safely(url)
            soup = BeautifulSoup(html_content, "xml")
            urls = []
            for loc in soup.find_all("loc"):
                loc_text = loc.text.strip()
                if self.is_safe_url(loc_text):
                    urls.append(loc_text)
            return urls
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to fetch sitemap: {e}")
            return []

    def extract_json_ld(self, soup):
        json_lds = []
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                json_lds.append(json.loads(script.string))
            except (json.JSONDecodeError, TypeError):
                pass
        return json_lds

    def _parse_faq_pricing(self, faq_list, service_name, location_name=None):
        pricing = {"amount": None, "currency": "INR", "type": None, "unit": None}
        description = None

        for faq in faq_list:
            if faq.get("@type") == "Question":
                q_text = faq.get("name", "").lower()
                a_text = faq.get("acceptedAnswer", {}).get("text", "")

                # Check for description
                if "what is" in q_text and "utservio" in q_text:
                    description = a_text

                # Match service name and capture price details
                if service_name.lower() in a_text.lower() and "₹" in a_text:
                    import re

                    # Match "starts at just ₹149 per fan" or "starts at ₹149 per fan"
                    match = re.search(
                        r"(?:starts at|from)\s*(?:just\s*)?₹\s*(\d+)\s*(?:per\s*(\w+))?",
                        a_text.lower(),
                    )
                    if match:
                        pricing["amount"] = str(match.group(1))
                        pricing["type"] = "starting_from"
                        unit_val = match.group(2)
                        if unit_val in ["fan", "room", "task"]:
                            pricing["unit"] = f"per {unit_val}"
                        elif "per fan" in a_text.lower():
                            pricing["unit"] = "per fan"
                        elif "per room" in a_text.lower():
                            pricing["unit"] = "per room"

        return pricing, description

    def _parse_html_pricing(self, soup, service_name):
        pricing = {"amount": None, "currency": "INR", "type": None, "unit": None}
        text = soup.get_text().lower()
        if "starts at" in text and "₹" in text:
            import re

            # Match: starts at [just] ₹149 per fan
            match = re.search(
                r"(?:starts at|from)\s*(?:just\s*)?₹\s*(\d+)\s*(?:per\s*(\w+))?", text
            )
            if match:
                pricing["amount"] = str(match.group(1))
                pricing["type"] = "starting_from"
                unit_str = match.group(2)
                if unit_str in ["fan", "room", "task"]:
                    pricing["unit"] = f"per {unit_str}"
                elif "per fan" in text:
                    pricing["unit"] = "per fan"
                elif "per room" in text:
                    pricing["unit"] = "per room"
        return pricing

    async def scrape_page(self, url):
        try:
            html_content = await self.fetch_page_safely(url)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Failed to fetch {url}: {e}")
            return None

        soup = BeautifulSoup(html_content, "html.parser")

        path = urlparse(url).path
        parts = [p for p in path.strip("/").split("/") if p]

        if not parts:
            return None

        if parts[0] in ["about", "privacy-policy", "terms-conditions"]:
            return None

        service_slug = parts[0]
        location_slug = parts[1] if len(parts) > 1 else None

        service_name = service_slug.replace("-", " ").title()
        location_name = (
            location_slug.replace("-", " ").title() if location_slug else None
        )
        if location_name and location_name.lower() == "omr":
            location_name = "OMR (Old Mahabalipuram Road)"

        json_lds = self.extract_json_ld(soup)

        pricing = {"amount": None, "currency": "INR", "type": None, "unit": None}
        description = f"Professional {service_name.lower()} at your doorstep."
        method = "semantic_html"

        # 1. JSON-LD First
        faq_found = False
        for ld in json_lds:
            if ld.get("@type") == "FAQPage":
                faq_list = ld.get("mainEntity", [])
                extracted_pricing, ext_desc = self._parse_faq_pricing(
                    faq_list, service_name, location_name
                )
                if extracted_pricing["amount"]:
                    pricing = extracted_pricing
                    method = "json_ld"
                    faq_found = True
                if ext_desc:
                    description = ext_desc

        # 2. HTML Fallback
        if not faq_found:
            html_pricing = self._parse_html_pricing(soup, service_name)
            if html_pricing["amount"]:
                pricing = html_pricing
                method = "semantic_html"

        # 3. Controlled text fallback
        if not pricing["amount"]:
            # E.g., check elements
            description_tag = soup.find("p", class_="text-lg text-stone-400")
            if description_tag:
                description = description_tag.get_text().strip()

        record = {
            "service_name": service_name,
            "category": "Home Cleaning",
            "description": description,
            "price_amount": pricing["amount"],
            "price_currency": pricing["currency"],
            "pricing_type": pricing["type"],
            "price_unit": pricing["unit"],
            "location_name": location_name,
            "source_url": url,
            "source_domain": self.domain,
            "extraction_method": method,
            "retrieved_at": datetime.now(timezone.utc),
        }

        return record

    async def close(self):
        await self.client.aclose()
