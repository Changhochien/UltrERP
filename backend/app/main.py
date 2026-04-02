from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from domains.customers.routes import router as customers_router
from domains.health.routes import router as health_router
from domains.invoices.routes import router as invoices_router
from domains.inventory.routes import router as inventory_router
from domains.orders.routes import router as orders_router


def create_app() -> FastAPI:
	app = FastAPI(title="UltrERP API", version="0.1.0")
	api_v1 = APIRouter(prefix="/api/v1")

	app.add_middleware(
		CORSMiddleware,
		allow_origins=list(settings.cors_origins),
		allow_credentials=True,
		allow_methods=["*"],
		allow_headers=["*"],
	)

	api_v1.include_router(health_router, prefix="/health", tags=["health"])
	api_v1.include_router(customers_router, prefix="/customers", tags=["customers"])
	api_v1.include_router(invoices_router, prefix="/invoices", tags=["invoices"])
	api_v1.include_router(inventory_router, prefix="/inventory", tags=["inventory"])
	api_v1.include_router(orders_router, prefix="/orders", tags=["orders"])
	app.include_router(api_v1)

	@app.get("/")
	async def root() -> dict[str, str]:
		return {"message": "UltrERP API", "version": "0.1.0"}

	return app


app = create_app()
