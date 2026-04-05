from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from common.database import AsyncSessionLocal
from domains.health.service import health_status

router = APIRouter()


def _database_unavailable(exc: SQLAlchemyError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="database unavailable",
    )


@router.get("")
async def get_health() -> dict[str, str | bool]:
    try:
        async with AsyncSessionLocal() as session:
            result = await health_status(session)
            result["mcp"] = True
            return result
    except SQLAlchemyError as exc:
        raise _database_unavailable(exc) from exc
