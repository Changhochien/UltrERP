"""S3-compatible object-store adapter.

Wraps boto3 (sync) behind a minimal protocol so domain code never touches
AWS/MinIO specifics directly.  The same interface is used in production
(MinIO with Object Lock) and in tests (in-memory fake).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Protocol


# ---------------------------------------------------------------------------
# Public data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PutResult:
	"""Metadata returned after a successful put_object."""
	object_key: str
	checksum_sha256: str
	byte_size: int
	content_type: str


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------

class ObjectStore(Protocol):
	"""Minimal object-store contract used by domain services."""

	def put_object(
		self,
		bucket: str,
		key: str,
		data: bytes,
		content_type: str = "application/xml",
	) -> PutResult: ...

	def get_object(self, bucket: str, key: str) -> bytes: ...


# ---------------------------------------------------------------------------
# In-memory fake for unit / integration tests
# ---------------------------------------------------------------------------

class InMemoryObjectStore:
	"""Thread-safe-enough fake for single-process test runs."""

	def __init__(self) -> None:
		self._objects: dict[tuple[str, str], bytes] = {}

	def put_object(
		self,
		bucket: str,
		key: str,
		data: bytes,
		content_type: str = "application/xml",
	) -> PutResult:
		self._objects[(bucket, key)] = data
		return PutResult(
			object_key=key,
			checksum_sha256=hashlib.sha256(data).hexdigest(),
			byte_size=len(data),
			content_type=content_type,
		)

	def get_object(self, bucket: str, key: str) -> bytes:
		try:
			return self._objects[(bucket, key)]
		except KeyError:
			raise FileNotFoundError(f"No object at {bucket}/{key}")

	@property
	def stored(self) -> dict[tuple[str, str], bytes]:
		"""Expose internal storage for test assertions."""
		return dict(self._objects)


# ---------------------------------------------------------------------------
# S3-compatible implementation (MinIO / AWS S3)
# ---------------------------------------------------------------------------

class S3ObjectStore:
	"""Production adapter — requires ``boto3`` at runtime."""

	def __init__(
		self,
		endpoint_url: str,
		access_key: str,
		secret_key: str,
		region: str = "us-east-1",
	) -> None:
		import boto3  # deferred import — only needed when actually used

		self._client = boto3.client(
			"s3",
			endpoint_url=endpoint_url,
			aws_access_key_id=access_key,
			aws_secret_access_key=secret_key,
			region_name=region,
		)

	def put_object(
		self,
		bucket: str,
		key: str,
		data: bytes,
		content_type: str = "application/xml",
	) -> PutResult:
		sha = hashlib.sha256(data).hexdigest()
		self._client.put_object(
			Bucket=bucket,
			Key=key,
			Body=data,
			ContentType=content_type,
			ChecksumSHA256=sha,
		)
		return PutResult(
			object_key=key,
			checksum_sha256=sha,
			byte_size=len(data),
			content_type=content_type,
		)

	def get_object(self, bucket: str, key: str) -> bytes:
		resp = self._client.get_object(Bucket=bucket, Key=key)
		return resp["Body"].read()


# ---------------------------------------------------------------------------
# Failing stub for tests that assert error paths
# ---------------------------------------------------------------------------

class FailingObjectStore:
	"""Always raises — used to verify error-handling paths."""

	def put_object(
		self,
		bucket: str,
		key: str,
		data: bytes,
		content_type: str = "application/xml",
	) -> PutResult:
		raise ConnectionError("Object store unavailable")

	def get_object(self, bucket: str, key: str) -> bytes:
		raise ConnectionError("Object store unavailable")
