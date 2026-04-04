from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app
from domains.health import routes as health_routes


class HealthySession:
    async def execute(self, _statement: object) -> None:
        return None


class FailingSession:
    async def execute(self, _statement: object) -> None:
        raise SQLAlchemyError("database unavailable")


class FakeSessionContext:
    def __init__(
        self,
        session: object | None = None,
        *,
        enter_error: SQLAlchemyError | None = None,
        exit_error: SQLAlchemyError | None = None,
    ) -> None:
        self.session = session
        self.enter_error = enter_error
        self.exit_error = exit_error

    async def __aenter__(self) -> object:
        if self.enter_error is not None:
            raise self.enter_error

        return self.session

    async def __aexit__(self, _exc_type, _exc, _tb) -> bool:
        if self.exit_error is not None:
            raise self.exit_error

        return False


async def test_health_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(
        health_routes,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(HealthySession()),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "mcp": True}


async def test_health_endpoint_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(
        health_routes,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(FailingSession()),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}


async def test_health_endpoint_returns_503_when_database_session_cannot_be_created(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        health_routes,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(enter_error=SQLAlchemyError("database unavailable")),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}


async def test_health_endpoint_returns_503_when_database_session_teardown_fails(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        health_routes,
        "AsyncSessionLocal",
        lambda: FakeSessionContext(
            HealthySession(),
            exit_error=SQLAlchemyError("database unavailable"),
        ),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "database unavailable"}
