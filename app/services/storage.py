from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

from app.services.secure_image_upload import persist_image


class Storage(Protocol):
    backend: str

    def save(self, data: bytes, extension: str, mime_type: str) -> tuple[str, str]: ...
    def url_for(self, object_key: str) -> str: ...
    def delete(self, object_key: str) -> None: ...


class LocalStorage:
    """Local filesystem storage using the existing secure upload pipeline."""

    backend = "local"

    def __init__(self, upload_dir: str):
        self.upload_dir = upload_dir

    def save(self, data: bytes, extension: str, mime_type: str) -> tuple[str, str]:
        # persist_image performs the existing safe local write and returns
        # the stored object key and SHA-256 digest.
        return persist_image(data, self.upload_dir, extension)

    def url_for(self, object_key: str) -> str:
        return f"/media/{object_key}"

    def delete(self, object_key: str) -> None:
        root = Path(self.upload_dir).resolve()
        path = (root / object_key).resolve()
        # Permit deletion only of files contained by the configured upload
        # directory; reject traversal and never follow an outside path.
        try:
            path.relative_to(root)
        except ValueError:
            raise ValueError("Invalid local storage object key.") from None
        if path.is_file():
            path.unlink()


def get_storage() -> Storage:
    """Return local storage; S3 activation is intentionally deferred."""
    return LocalStorage(os.getenv("UPLOAD_DIR", "uploads"))
