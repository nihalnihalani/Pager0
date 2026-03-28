"""Shared request verification helpers for inbound webhooks."""

from __future__ import annotations

import hashlib
import hmac


def compute_hmac_sha256(secret: str, body: bytes) -> str:
    """Return the lowercase hex SHA-256 HMAC for *body*."""
    return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


def verify_hmac_sha256(secret: str, body: bytes, signature: str | None) -> bool:
    """Verify a webhook signature against the request body.

    Accepts either the raw hex digest or a ``sha256=<digest>`` formatted value.
    """
    if not secret or not signature:
        return False

    normalized = signature.strip()
    if normalized.startswith("sha256="):
        normalized = normalized.split("=", 1)[1]

    expected = compute_hmac_sha256(secret, body)
    return hmac.compare_digest(expected, normalized)
