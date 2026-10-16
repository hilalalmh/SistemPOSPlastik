import hashlib
import json
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError
from app.models.user import IdempotencyKey


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def check_idempotency(
    db: Session, *, user_id: UUID, endpoint: str, key: str, payload: Any
) -> tuple[bool, dict | None, int | None]:
    """Return (is_replay, response_body, status_code)."""
    request_hash = _hash_payload(payload)
    existing = db.execute(
        select(IdempotencyKey).where(IdempotencyKey.key == key)
    ).scalar_one_or_none()

    if existing is None:
        return False, None, None
    if existing.request_hash != request_hash:
        raise ConflictError(
            "Idempotency-Key sudah dipakai dengan data berbeda.",
            code="IDEMPOTENCY_CONFLICT",
        )
    return True, existing.response_body, existing.status_code


def store_idempotency(
    db: Session,
    *,
    user_id: UUID,
    endpoint: str,
    key: str,
    payload: Any,
    status_code: int,
    response_body: dict,
) -> None:
    db.add(
        IdempotencyKey(
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            request_hash=_hash_payload(payload),
            status_code=status_code,
            response_body=response_body,
        )
    )
    db.flush()
