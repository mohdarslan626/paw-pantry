from __future__ import annotations

import io
import os
import socket
import struct
import warnings
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_IMAGE_PIXELS = 40_000_000
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
CHUNK_SIZE = 64 * 1024


class ImageUploadError(ValueError):
    """The upload is not a safe, supported image."""


class MalwareScannerUnavailable(RuntimeError):
    """The required malware scanner cannot be reached or did not respond."""


def scan_with_clamav(data: bytes) -> None:
    """Scan raw upload bytes using ClamAV's INSTREAM protocol; fail closed."""
    host = os.getenv("CLAMAV_HOST", "127.0.0.1")
    port = int(os.getenv("CLAMAV_PORT", "3310"))
    timeout = float(os.getenv("CLAMAV_TIMEOUT_SECONDS", "20"))

    try:
        with socket.create_connection((host, port), timeout=timeout) as client:
            client.settimeout(timeout)
            client.sendall(b"zINSTREAM\0")
            for offset in range(0, len(data), CHUNK_SIZE):
                chunk = data[offset : offset + CHUNK_SIZE]
                client.sendall(struct.pack("!I", len(chunk)) + chunk)
            client.sendall(struct.pack("!I", 0))
            response = bytearray()
            while not response.endswith(b"\0") and len(response) < 4096:
                part = client.recv(1024)
                if not part:
                    break
                response.extend(part)
    except (OSError, TimeoutError) as exc:
        raise MalwareScannerUnavailable("Malware scanning is temporarily unavailable.") from exc

    result = bytes(response).decode("utf-8", errors="replace").strip("\0\r\n ")
    if not result.endswith("OK"):
        if "FOUND" in result:
            raise ImageUploadError("The uploaded file was flagged by malware scanning.")
        raise MalwareScannerUnavailable("Malware scanner returned an invalid response.")


def normalize_image(data: bytes) -> tuple[bytes, str, str]:
    """Validate and re-encode an image, stripping metadata and active payloads."""
    if not data:
        raise ImageUploadError("The uploaded file is empty.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ALLOWED_FORMATS:
                    raise ImageUploadError("Only JPEG, PNG, and WebP images are accepted.")
                if getattr(image, "n_frames", 1) != 1:
                    raise ImageUploadError("Animated images are not accepted.")
                if image.width < 1 or image.height < 1:
                    raise ImageUploadError("The image dimensions are invalid.")
                if image.width * image.height > MAX_IMAGE_PIXELS:
                    raise ImageUploadError("The image dimensions exceed the allowed limit.")
                image.verify()

            with Image.open(io.BytesIO(data)) as image:
                image.load()
                image = ImageOps.exif_transpose(image)
                if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
                    image = image.convert("RGBA")
                else:
                    image = image.convert("RGB")
                output = io.BytesIO()
                image.save(output, format="WEBP", quality=85, method=4)
                normalized = output.getvalue()
    except ImageUploadError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageUploadError("The file is not a valid, safely decodable image.") from exc

    if not normalized:
        raise ImageUploadError("The image could not be processed.")
    return normalized, "image/webp", ".webp"


def persist_image(data: bytes, upload_dir: str, extension: str) -> tuple[str, str]:
    """Persist only normalized bytes under an opaque, server-generated key."""
    import hashlib
    import uuid

    key = f"{uuid.uuid4().hex}{extension}"
    root = Path(upload_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = (root / key).resolve()
    if destination.parent != root:
        raise RuntimeError("Unsafe upload destination.")
    with destination.open("xb") as output:
        output.write(data)
    return key, hashlib.sha256(data).hexdigest()
