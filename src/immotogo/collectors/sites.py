"""Site-specific collectors for Togolese real-estate portals."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from itertools import islice
from typing import AsyncIterator, Iterable
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from immotogo.collectors.base import BaseCollector
from immotogo.data.schemas import Listing, PropertyType, TransactionType

logger = logging.getLogger(__name__)


_PRICE_RE = re.compile(r"([0-9][0-9\s.,]+)")
_SURFACE_RE = re.compile(r"([0-9]+)\s?m\s?²", re.IGNORECASE)
_BEDROOM_RE = re.compile(r"([0-9]+)\s?(ch|chambre)s?", re.IGNORECASE)


class CoinAfriqueCollector(BaseCollector):
    """Collector for the CoinAfrique TG portal."""

    name = "coin_afrique"
    base_url = "https://tg.coinafrique.com/categorie/immobilier"

    async def collect(self) -> AsyncIterator[Listing]:
        html = await self.fetch_html(self.base_url)
        parser = HTMLParser(html)
        cards = parser.css("a.ad")
        for card in cards:
            try:
                url = urljoin(self.base_url, card.attributes.get("href", ""))
                title = (card.css_first("h3") or card.css_first("h2")).text(strip=True)
                description = card.text(separator=" ", strip=True)
                price_text = (card.css_first(".price") or card).text(strip=True)
                price, currency = _parse_price(price_text)
                property_type = _guess_property_type(title + " " + description)
                transaction_type = _guess_transaction_type(title + " " + description)
                location = card.css_first(".location").text(strip=True) if card.css_first(".location") else None
                surface = _parse_surface(description)
                bedrooms = _parse_bedrooms(description)
                images = [img.attributes.get("src") for img in card.css("img") if img.attributes.get("src")]
                listing = Listing(
                    id=url,
                    source=self.name,
                    title=title,
                    description=description,
                    property_type=property_type,
                    transaction_type=transaction_type,
                    city=location,
                    price=price,
                    currency=currency,
                    surface_m2=surface,
                    bedrooms=bedrooms,
                    url=url,
                    images=images,
                    scraped_at=self._now(),
                )
                yield listing
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to parse CoinAfrique card: %s", exc, exc_info=True)
                continue


class ImmoOzCollector(BaseCollector):
    """Collector for ImmoOz portal."""

    name = "immooz"
    base_url = "https://immooz.com/tg/"

    async def collect(self) -> AsyncIterator[Listing]:
        html = await self.fetch_html(self.base_url)
        parser = HTMLParser(html)
        cards = parser.css("div.property-item")
        for card in cards:
            try:
                anchor = card.css_first("a")
                url = urljoin(self.base_url, anchor.attributes.get("href", ""))
                title = anchor.text(strip=True)
                description = card.text(separator=" ", strip=True)
                price_text = (card.css_first(".property-price") or card).text(strip=True)
                price, currency = _parse_price(price_text)
                property_type = _guess_property_type(title + " " + description)
                transaction_type = _guess_transaction_type(title + " " + description)
                location = card.css_first(".property-location").text(strip=True) if card.css_first(".property-location") else None
                surface = _parse_surface(description)
                bedrooms = _parse_bedrooms(description)
                images = [img.attributes.get("data-src") or img.attributes.get("src") for img in card.css("img") if img.attributes.get("src") or img.attributes.get("data-src")]
                listing = Listing(
                    id=url,
                    source=self.name,
                    title=title,
                    description=description,
                    property_type=property_type,
                    transaction_type=transaction_type,
                    city=location,
                    price=price,
                    currency=currency,
                    surface_m2=surface,
                    bedrooms=bedrooms,
                    url=url,
                    images=[img for img in images if img],
                    scraped_at=self._now(),
                )
                yield listing
            except Exception as exc:  # pragma: no cover
                logger.warning("Failed to parse ImmoOz card: %s", exc, exc_info=True)
                continue


async def collect_all(concurrency: int = 5) -> list[Listing]:
    """Convenience helper that fans out across all collectors."""

    collectors: Iterable[BaseCollector] = [CoinAfriqueCollector(), ImmoOzCollector()]

    async def _collect_from(collector: BaseCollector) -> list[Listing]:
        results: list[Listing] = []
        async with collector:
            async for listing in islice(collector.collect(), 200):
                results.append(listing)
        return results

    semaphore = asyncio.Semaphore(concurrency)

    async def _task(collector: BaseCollector) -> list[Listing]:
        async with semaphore:
            return await _collect_from(collector)

    tasks = [asyncio.create_task(_task(collector)) for collector in collectors]
    gathered = await asyncio.gather(*tasks, return_exceptions=True)

    listings: list[Listing] = []
    for collector, result in zip(collectors, gathered, strict=False):
        if isinstance(result, Exception):
            logger.error("Collector %s failed: %s", collector.name, result)
            continue
        listings.extend(result)
    return listings


def _parse_price(text: str) -> tuple[float | None, str]:
    match = _PRICE_RE.search(text.replace(" ", " "))
    if not match:
        return None, "XOF"
    value = float(match.group(1).replace(" ", "").replace(",", "."))
    currency = "XOF"
    text_upper = text.upper()
    if "F CFA" in text_upper or "FCFA" in text_upper:
        currency = "XOF"
    elif "€" in text_upper:
        currency = "EUR"
    elif "$" in text_upper:
        currency = "USD"
    return value, currency


def _parse_surface(text: str) -> float | None:
    match = _SURFACE_RE.search(text)
    if not match:
        return None
    return float(match.group(1))


def _parse_bedrooms(text: str) -> int | None:
    match = _BEDROOM_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


def _guess_property_type(text: str) -> PropertyType:
    text_lower = text.lower()
    if any(word in text_lower for word in ["appartement", "studio", "duplex"]):
        return PropertyType.apartment
    if any(word in text_lower for word in ["maison", "villa"]):
        return PropertyType.house
    if any(word in text_lower for word in ["bureau", "bureau commercial", "plateau"]):
        return PropertyType.office
    if "terrain" in text_lower:
        return PropertyType.land
    if any(word in text_lower for word in ["magasin", "commerce", "boutique"]):
        return PropertyType.commercial
    return PropertyType.other


def _guess_transaction_type(text: str) -> TransactionType:
    text_lower = text.lower()
    if any(word in text_lower for word in ["location", "louer", "loyer"]):
        return TransactionType.rent
    if any(word in text_lower for word in ["vente", "vendre", "acheter", "achat"]):
        return TransactionType.sale
    return TransactionType.rent
