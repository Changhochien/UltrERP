from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(slots=True)
class DomainEvent:
	name: str
	occurred_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
