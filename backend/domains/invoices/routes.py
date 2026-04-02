"""Invoice API routes."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from common.database import get_db
from common.errors import ValidationError, error_response
from domains.invoices.pdf import DEFAULT_SELLER, generate_invoice_pdf, pdf_filename
from domains.invoices.schemas import InvoiceCreate, InvoiceResponse, VoidInvoiceRequest
from domains.invoices.service import create_invoice, get_invoice, void_invoice
from domains.invoices.validators import IMMUTABLE_ERROR

router = APIRouter()

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post(
	"",
	response_model=InvoiceResponse,
	status_code=status.HTTP_201_CREATED,
)
async def create(data: InvoiceCreate, session: DbSession) -> InvoiceResponse | JSONResponse:
	try:
		invoice = await create_invoice(session, data)
		return InvoiceResponse.model_validate(invoice)
	except ValidationError as exc:
		return JSONResponse(
			status_code=422,
			content=error_response(exc.errors),
		)


@router.get(
	"/{invoice_id}",
	response_model=InvoiceResponse,
)
async def get(invoice_id: uuid.UUID, session: DbSession) -> InvoiceResponse | JSONResponse:
	invoice = await get_invoice(session, invoice_id)
	if invoice is None:
		return JSONResponse(
			status_code=404,
			content={"detail": "Invoice not found"},
		)
	return InvoiceResponse.model_validate(invoice)


@router.post(
	"/{invoice_id}/void",
	response_model=InvoiceResponse,
)
async def void(
	invoice_id: uuid.UUID,
	data: VoidInvoiceRequest,
	session: DbSession,
) -> InvoiceResponse | JSONResponse:
	try:
		invoice = await void_invoice(session, invoice_id, reason=data.reason)
		return InvoiceResponse.model_validate(invoice)
	except ValueError as exc:
		msg = str(exc)
		if msg == "Invoice not found":
			return JSONResponse(
				status_code=404,
				content={"detail": msg},
			)
		return JSONResponse(
			status_code=422,
			content=error_response([{"field": "invoice", "message": msg}]),
		)


@router.get("/{invoice_id}/pdf", response_model=None)
async def export_pdf(
	invoice_id: uuid.UUID,
	session: DbSession,
) -> Response | JSONResponse:
	invoice = await get_invoice(session, invoice_id)
	if invoice is None:
		return JSONResponse(
			status_code=404,
			content={"detail": "Invoice not found"},
		)
	try:
		pdf_bytes = generate_invoice_pdf(invoice, DEFAULT_SELLER)
	except ValueError as exc:
		return JSONResponse(
			status_code=422,
			content=error_response([{"field": "invoice", "message": str(exc)}]),
		)
	except RuntimeError as exc:
		return JSONResponse(
			status_code=503,
			content={"detail": str(exc)},
		)
	filename = pdf_filename(invoice)
	return Response(
		content=pdf_bytes,
		media_type="application/pdf",
		headers={"Content-Disposition": f'attachment; filename="{filename}"'},
	)


@router.put(
	"/{invoice_id}",
	status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
async def update_rejected(invoice_id: uuid.UUID) -> JSONResponse:
	"""Reject any PUT update — invoices are immutable after creation."""
	return JSONResponse(
		status_code=405,
		content={"detail": IMMUTABLE_ERROR},
	)


@router.patch(
	"/{invoice_id}",
	status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
async def patch_rejected(invoice_id: uuid.UUID) -> JSONResponse:
	"""Reject any PATCH update — invoices are immutable after creation."""
	return JSONResponse(
		status_code=405,
		content={"detail": IMMUTABLE_ERROR},
	)


@router.delete(
	"/{invoice_id}",
	status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
)
async def delete_rejected(invoice_id: uuid.UUID) -> JSONResponse:
	"""Reject any DELETE — invoices are immutable; use void instead."""
	return JSONResponse(
		status_code=405,
		content={"detail": IMMUTABLE_ERROR},
	)