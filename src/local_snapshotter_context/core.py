"""Core implementation for Local Snapshotter Context.

The purpose of this module is to provide a compact, self-contained serialization
format for a flat mapping of string keys to JSON-serializable values.  The
serialized form is a single URL-safe base64 string so it can be passed through
environment variables, command-line arguments, or any process-boundary channel
that tolerates ASCII text.
"""

from __future__ import annotations

import base64
import json
import zlib
from typing import Any, Dict, Mapping


class SnapshotError(ValueError):
    """Raised when a token cannot be decoded or violates the expected schema."""


_PREFIX = b"LSC1:"


def _normalize_mapping(context: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a plain dict copy of *context*.

    We copy rather than reference so later mutation of the caller's mapping
    cannot silently change what a previously issued token represents.
    """
    return dict(context)


def capture(context: Mapping[str, Any], *, compress: bool = True) -> str:
    """Serialize *context* into an opaque URL-safe token string.

    Args:
        context: A mapping whose keys are strings and whose values are
            JSON-serializable.
        compress: If true (the default), the JSON payload is deflate-compressed
            before base64 encoding.  Compression is transparent to `restore`,
            which detects the framing prefix.

    Returns:
        A str token.  The token is pure ASCII and safe to embed in a URL query
        component without further quoting, though callers should still treat it
        as opaque.

    Raises:
        TypeError: If a key is not a str, or a value is not JSON-serializable.
    """
    normalized = _normalize_mapping(context)

    # Fail early with a clear TypeError for non-string keys.  json.dumps would
    # silently coerce integer keys to strings, which would violate the
    # round-trip guarantee for keys.
    for key in normalized:
        if not isinstance(key, str):
            raise TypeError(f"context keys must be str, got {type(key).__name__}")

    payload = json.dumps(
        normalized,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")

    if compress:
        compressed = zlib.compress(payload, level=6)
        body = compressed
    else:
        body = payload

    token = base64.urlsafe_b64encode(_PREFIX + body).decode("ascii")
    return token


def restore(token: str) -> Dict[str, Any]:
    """Decode a token produced by `capture` back into a dict.

    The returned dict is always a fresh, mutable plain dict.  The caller may
    mutate it without affecting any other token or original context object.

    Args:
        token: A str previously returned by `capture`.

    Returns:
        A dict with the same string keys and JSON values as the original
        mapping.

    Raises:
        SnapshotError: If the token is malformed, has an unknown framing
            prefix, or contains data that is not a JSON object with string
            keys.
    """
    if not isinstance(token, str):
        raise SnapshotError(f"token must be str, got {type(token).__name__}")

    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
    except (UnicodeEncodeError, ValueError) as exc:
        raise SnapshotError("token is not valid base64") from exc

    if not raw.startswith(_PREFIX):
        raise SnapshotError("token has unsupported framing prefix")

    body = raw[len(_PREFIX):]

    # Auto-detect compression: if the body is not valid UTF-8 JSON, assume it
    # is zlib-compressed and try to decompress.  This keeps `restore` compatible
    # with both `capture(..., compress=True)` and `capture(..., compress=False)`
    # without embedding a second flag in the token.
    try:
        payload = body.decode("utf-8")
    except UnicodeDecodeError:
        try:
            payload = zlib.decompress(body).decode("utf-8")
        except (zlib.error, UnicodeDecodeError) as exc:
            raise SnapshotError("token payload is not valid compressed JSON") from exc

    try:
        decoded = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SnapshotError("token payload is not valid JSON") from exc

    if not isinstance(decoded, dict):
        raise SnapshotError("token payload must decode to a JSON object")

    for key in decoded:
        if not isinstance(key, str):
            raise SnapshotError("decoded object contains a non-string key")

    return decoded
