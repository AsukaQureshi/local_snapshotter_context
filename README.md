# Local Snapshotter Context

A tiny, dependency-free Python library that captures a flat mapping of string keys to JSON-serializable values as an opaque URL-safe token string, and restores that token back into a fresh dict.

## Usage

```python
from local_snapshotter_context import capture, restore

ctx = {"request_id": "abc-123", "user": "alice", "attempt": 3}
token = capture(ctx)

# Pass `token` across a process boundary, e.g. environment variable or argv.
# Later, in another process:
restored = restore(token)
print(restored)
# {'attempt': 3, 'request_id': 'abc-123', 'user': 'alice'}
```

The token is pure ASCII, safe for a URL query component, and deterministic for the same input mapping. Key order does not matter.

## Why this exists

Propagating a small amount of structured context between processes is often done by passing a JSON blob as a command-line argument or environment variable. That works, but the raw JSON is verbose, can contain characters that need escaping, and gives no guarantee about key ordering or shape. This library wraps that pattern in a compact, compressed, URL-safe token with a framing prefix so a receiving process can detect that the token is one of ours and decode it without separate metadata.

The main trade-off is that values must be JSON-serializable. This covers most practical propagation needs, but it is not a general object serializer. Non-string keys are rejected explicitly rather than silently coerced.

## Awkward edge to be aware of

Compression is enabled by default, but `restore` transparently handles both compressed and uncompressed tokens. If you hand-write a token with a valid `LSC1:` prefix but an invalid payload, `restore` raises `SnapshotError` instead of returning garbage.

## Exports

- `capture(context, *, compress=True) -> str`  
  Serialize a mapping into a token. Raises `TypeError` for non-string keys or non-serializable values.
- `restore(token) -> dict`  
  Decode a token back into a fresh dict. Raises `SnapshotError` for malformed tokens.
- `SnapshotError`  
  Exception type raised by `restore` for invalid tokens.

## Performance

The window keeps a bounded buffer, so `push` is constant time and memory does not
grow with the length of the stream. `peak` and `trough` are linear in the window
size, which is the trade that keeps `push` cheap.

## Limitations

Values are coerced to floats, so very large integers lose precision. If you need
exact integer aggregates over a window, this is the wrong tool.

