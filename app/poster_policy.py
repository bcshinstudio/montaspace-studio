"""Pure, platform-neutral poster identity and retry policy.

Poster success and failure markers are tied to a particular file version
(path + size + nanosecond mtime); editing the source naturally permits a new
attempt without periodic polling.
"""
import hashlib
import os
from pathlib import Path


def source_version_key(filename):
    source = Path(filename).resolve()
    stat = source.stat()
    identity = f"{os.path.normcase(str(source))}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def failed_marker_name(key):
    if len(key) != 64 or any(c not in "0123456789abcdef" for c in key):
        raise ValueError("Invalid poster cache key")
    return key + ".failed"
