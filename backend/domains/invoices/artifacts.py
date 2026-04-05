"""Artifact orchestration — generate, store, and record invoice artifacts."""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from common.object_store import ObjectStore, PutResult
from domains.invoices.artifact_model import InvoiceArtifact
from domains.invoices.mig41 import generate_mig41_xml

if TYPE_CHECKING:
    from domains.invoices.models import Invoice

ARTIFACT_BUCKET = "invoice-artifacts"
ARTIFACT_KIND_MIG41 = "mig41-xml"


def _object_key(invoice: Invoice) -> str:
    return f"{invoice.tenant_id}/mig41/{invoice.id}.xml"


def _retention_until(invoice_date: date) -> str:
    """10-year retention baseline from the invoice date."""
    return str(invoice_date.year + 10) + invoice_date.strftime("-%m-%d")


async def archive_invoice_xml(
    session: AsyncSession,
    invoice: Invoice,
    store: ObjectStore,
    *,
    seller_ban: str = "000000000",
    seller_name: str = "UltrERP",
    retention_class: str = "legal-10y",
    storage_policy: str = "standard",
) -> InvoiceArtifact:
    """Generate MIG 4.1 XML, upload to object store, persist metadata.

    Raises:
            MIG41Error: If the invoice cannot produce valid XML.
            ConnectionError: If the object store is unreachable.
    """
    xml_bytes = generate_mig41_xml(
        invoice,
        seller_ban=seller_ban,
        seller_name=seller_name,
    )

    key = _object_key(invoice)
    retention_until = _retention_until(invoice.invoice_date)
    result: PutResult = store.put_object(
        bucket=ARTIFACT_BUCKET,
        key=key,
        data=xml_bytes,
        content_type="application/xml",
        storage_policy=storage_policy,
        retention_until=retention_until,
    )

    if not result.checksum_sha256 or result.byte_size <= 0:
        raise ConnectionError(
            f"Object store returned invalid result for key={key}: "
            f"checksum={result.checksum_sha256!r}, size={result.byte_size}"
        )

    artifact = InvoiceArtifact(
        id=uuid.uuid4(),
        tenant_id=invoice.tenant_id,
        invoice_id=invoice.id,
        artifact_kind=ARTIFACT_KIND_MIG41,
        object_key=result.object_key,
        content_type=result.content_type,
        checksum_sha256=result.checksum_sha256,
        byte_size=result.byte_size,
        retention_class=retention_class,
        retention_until=retention_until,
        storage_policy=result.storage_policy,
    )

    session.add(artifact)
    return artifact
