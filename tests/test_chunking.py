from datetime import datetime

from immotogo.data.schemas import Listing, PropertyType, TransactionType
from immotogo.pipeline.ingest import chunk_listing


def make_listing() -> Listing:
    return Listing(
        id="test",
        source="test",
        title="Appartement moderne à Lomé",
        description="Superbe appartement avec deux chambres, proche de la plage.",
        property_type=PropertyType.apartment,
        transaction_type=TransactionType.rent,
        city="Lomé",
        price=250000,
        currency="XOF",
        surface_m2=120,
        bedrooms=2,
        url="https://example.com",
        scraped_at=datetime.utcnow(),
    )


def test_chunking_returns_chunks():
    listing = make_listing()
    chunks = chunk_listing(listing, chunk_size=5)
    assert len(chunks) >= 1
    assert chunks[0].listing_id == listing.id
