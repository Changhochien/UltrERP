"""Tests for XML sitemap generation — Story 10.2."""

from __future__ import annotations

import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from common.tenant import DEFAULT_TENANT_ID
from domains.aeo import sitemap as sitemap_mod

_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
_DEFAULT_BASE = "http://localhost:8000"


# ── Helpers ───────────────────────────────────────────────────

_UNSET = object()


def _make_product(
    *,
    status: str = "active",
    tenant_id: uuid.UUID = DEFAULT_TENANT_ID,
    product_id: uuid.UUID | None = None,
    code: str = "P-001",
    updated_at: datetime | None | object = _UNSET,
) -> MagicMock:
    p = MagicMock()
    p.id = product_id or uuid.uuid4()
    p.tenant_id = tenant_id
    p.code = code
    p.status = status
    # Use sentinel to distinguish "not passed" from explicitly None
    if updated_at is _UNSET:
        p.updated_at = datetime(2026, 4, 1, 12, 0, 0, tzinfo=timezone.utc)
    else:
        p.updated_at = updated_at
    return p


def _mock_settings(base_url: str = _DEFAULT_BASE, cache_ttl: int = 3600) -> MagicMock:
    s = MagicMock()
    s.public_base_url = base_url
    s.sitemap_cache_ttl = cache_ttl
    return s


def _parse_xml(xml_bytes: bytes) -> ET.Element:
    return ET.fromstring(xml_bytes)


@pytest.fixture(autouse=True)
def _clear_sitemap_cache():
    """Ensure cache is cleared before and after each test."""
    sitemap_mod.invalidate_sitemap_cache()
    yield
    sitemap_mod.invalidate_sitemap_cache()


@pytest.fixture
def _override_db():
    from common.database import get_db

    def _set(mock_session):
        async def _fake_db():
            yield mock_session

        app.dependency_overrides[get_db] = _fake_db

    yield _set
    app.dependency_overrides.clear()


# ── Unit tests: generate_product_sitemap_xml ──────────────────


async def test_sitemap_valid_xml_with_namespace():
    """Generated sitemap has correct XML namespace."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [_make_product()]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    assert root.tag == f"{{{_NS['sm']}}}urlset"


async def test_sitemap_only_active_products():
    """Only active products appear in sitemap entries."""
    active = _make_product(status="active", code="A-001")

    # The query itself filters — simulate returning only active
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [active]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    urls = root.findall("sm:url", _NS)
    assert len(urls) == 1
    loc = urls[0].find("sm:loc", _NS)
    assert str(active.id) in loc.text


async def test_sitemap_loc_with_default_base_url():
    """`<loc>` uses default base URL when PUBLIC_BASE_URL not set."""
    pid = uuid.uuid4()
    product = _make_product(product_id=pid)

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [product]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings(_DEFAULT_BASE)):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    loc = root.find("sm:url/sm:loc", _NS)
    expected = f"{_DEFAULT_BASE}/api/v1/inventory/products/{pid}/jsonld"
    assert loc.text == expected


async def test_sitemap_loc_with_custom_base_url():
    """`<loc>` uses custom PUBLIC_BASE_URL."""
    pid = uuid.uuid4()
    product = _make_product(product_id=pid)
    custom_base = "https://erp.example.com"

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [product]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings(custom_base)):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    loc = root.find("sm:url/sm:loc", _NS)
    assert loc.text.startswith("https://erp.example.com/")


async def test_sitemap_lastmod_iso8601():
    """`<lastmod>` is ISO 8601 format."""
    dt = datetime(2026, 4, 1, 12, 30, 0, tzinfo=timezone.utc)
    product = _make_product(updated_at=dt)

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [product]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    lastmod = root.find("sm:url/sm:lastmod", _NS)
    assert lastmod.text == "2026-04-01T12:30:00+00:00"


async def test_sitemap_omits_lastmod_when_updated_at_none():
    """`<lastmod>` is omitted when product.updated_at is None."""
    product = _make_product(updated_at=None)

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [product]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    lastmod = root.find("sm:url/sm:lastmod", _NS)
    assert lastmod is None


async def test_sitemap_empty_for_no_active_products():
    """Empty sitemap when no active products exist."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    urls = root.findall("sm:url", _NS)
    assert len(urls) == 0


async def test_sitemap_xml_declaration_present():
    """XML declaration <?xml ...?> is present."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    assert xml_bytes.startswith(b"<?xml")


async def test_sitemap_cache_invalidation():
    """invalidate_sitemap_cache clears cached XML."""
    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [_make_product(code="A-001")]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        first = await sitemap_mod.generate_product_sitemap_xml(db)
        # Should return cached (same object)
        second = await sitemap_mod.generate_product_sitemap_xml(db)
        assert first is second

        # Invalidate and regenerate
        sitemap_mod.invalidate_sitemap_cache()
        scalars_mock2 = MagicMock()
        scalars_mock2.all.return_value = [
            _make_product(code="A-001"),
            _make_product(code="B-002"),
        ]
        result_mock2 = MagicMock()
        result_mock2.scalars.return_value = scalars_mock2
        db.execute = AsyncMock(return_value=result_mock2)

        third = await sitemap_mod.generate_product_sitemap_xml(db)
        assert first is not third
        # Now has 2 URLs
        root = _parse_xml(third)
        assert len(root.findall("sm:url", _NS)) == 2


async def test_sitemap_changefreq_and_priority():
    """Each entry has changefreq=weekly and priority=0.6."""
    product = _make_product()

    db = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [product]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    db.execute = AsyncMock(return_value=result_mock)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        xml_bytes = await sitemap_mod.generate_product_sitemap_xml(db)

    root = _parse_xml(xml_bytes)
    url_el = root.find("sm:url", _NS)
    assert url_el.find("sm:changefreq", _NS).text == "weekly"
    assert url_el.find("sm:priority", _NS).text == "0.6"


# ── API integration tests ────────────────────────────────────


async def test_api_sitemap_returns_200_xml(_override_db):
    """GET /sitemap-products.xml returns 200 with application/xml."""
    mock_session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [_make_product()]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute = AsyncMock(return_value=result_mock)
    _override_db(mock_session)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/sitemap-products.xml")

    assert resp.status_code == 200
    assert "application/xml" in resp.headers["content-type"]


async def test_api_sitemap_returns_valid_xml_body(_override_db):
    """GET /sitemap-products.xml body is parseable XML with correct namespace."""
    mock_session = AsyncMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [_make_product()]
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    mock_session.execute = AsyncMock(return_value=result_mock)
    _override_db(mock_session)

    with patch.object(sitemap_mod, "get_settings", return_value=_mock_settings()):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.get("/sitemap-products.xml")

    root = ET.fromstring(resp.content)
    assert root.tag == f"{{{_NS['sm']}}}urlset"
    urls = root.findall("sm:url", _NS)
    assert len(urls) == 1


async def test_api_flush_sitemap_cache():
    """POST /api/v1/admin/sitemap-cache/invalidate flushes cache."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post("/api/v1/admin/sitemap-cache/invalidate")

    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
