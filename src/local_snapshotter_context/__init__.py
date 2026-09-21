"""Local Snapshotter Context.

Exports:
    capture: Capture a context-local snapshot as an opaque token string.
    restore: Restore a dict from a token string produced by capture.
    SnapshotError: Raised for malformed or incompatible tokens.
"""

from .core import capture, restore, SnapshotError

__all__ = ["capture", "restore", "SnapshotError"]
