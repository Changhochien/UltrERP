from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from app.mcp_setup import get_mcp_app
from common.config import settings
from common.database import get_db
from domains.aeo.sitemap import generate_product_sitemap_xml, invalidate_sitemap_cache
from domains.approval.routes import router as approval_router
from domains.audit.routes import router as audit_router
from domains.auth.routes import router as auth_router
from domains.customers.routes import router as customers_router
from domains.dashboard.routes import router as dashboard_router
from domains.health.routes import router as health_router
from domains.inventory.routes import router as inventory_router
from domains.invoices.routes import router as invoices_router
from domains.line.webhook import router as line_router
from domains.orders.routes import router as orders_router
from domains.payments.routes import router as payments_router
from domains.users.routes import router as users_router


def create_app() -> FastAPI:
	mcp_app = get_mcp_app()

	@asynccontextmanager
	async def lifespan(app: FastAPI):
		mcp_lifespan = mcp_app.router.lifespan_context
		async with mcp_lifespan(mcp_app):
			yield

	app = FastAPI(title="UltrERP API", version="0.1.0", lifespan=lifespan)
	api_v1 = APIRouter(prefix="/api/v1")

	app.add_middleware(
		CORSMiddleware,
		allow_origins=list(settings.cors_origins),
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	api_v1.include_router(health_router, prefix="/health", tags=["health"])
	api_v1.include_router(auth_router, prefix="/auth", tags=["auth"])
	api_v1.include_router(approval_router, prefix="/admin/approvals", tags=["approvals"])
	api_v1.include_router(audit_router, prefix="/admin/audit-logs", tags=["audit"])
	api_v1.include_router(users_router, prefix="/admin/users", tags=["users"])
	api_v1.include_router(customers_router, prefix="/customers", tags=["customers"])
	api_v1.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
	api_v1.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
	api_v1.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
	api_v1.include_router(line_router, prefix="/line", tags=["LINE"])
	api_v1.include_router(orders_router, prefix="/orders", tags=["orders"])
	api_v1.include_router(payments_router, prefix="/payments", tags=["payments"])
	app.include_router(api_v1)

	app.mount("/mcp", mcp_app)

	@app.get("/")
	async def root() -> dict[str, str]:
		return {"message": "UltrERP API", "version": "0.1.0"}

	@app.get("/sitemap-products.xml", include_in_schema=False)
	async def product_sitemap(
		db: AsyncSession = Depends(get_db),
	) -> Response:
		xml_bytes = await generate_product_sitemap_xml(db)
		return Response(content=xml_bytes, media_type="application/xml")

	@app.post("/api/v1/admin/sitemap-cache/invalidate", include_in_schema=False)
	async def flush_sitemap_cache() -> dict[str, str]:
		"""Flush sitemap cache. Call after bulk product imports or migrations."""
		invalidate_sitemap_cache()
		return {"status": "ok", "detail": "Sitemap cache invalidated"}

	return app


app = create_app()
