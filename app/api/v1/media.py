from __future__ import annotations

import os
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.db.session import get_db
from app.models.models import MediaAsset, MediaStatus, User
from app.services.secure_image_upload import (
    ImageUploadError,
    MalwareScannerUnavailable,
    normalize_image,
    persist_image,
    scan_with_clamav,
)

router = APIRouter(prefix="/media", tags=["Media"])
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024)))


class ImageUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    object_key: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str | None
    status: MediaStatus
    url: str


@router.post("/images", response_model=ImageUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
) -> ImageUploadResponse:
    """Admin-only upload; raw bytes are scanned and never stored as-is."""
    declared_type = (file.content_type or "").lower().split(";", 1)[0].strip()
    if declared_type and declared_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP uploads are accepted.")

    data = await file.read(MAX_UPLOAD_BYTES + 1)
    await file.close()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="The image exceeds the upload size limit.")
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        scan_with_clamav(data)
        normalized, mime_type, extension = normalize_image(data)
    except ImageUploadError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except MalwareScannerUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    upload_dir = os.getenv("UPLOAD_DIR", "uploads")
    object_key, checksum = persist_image(normalized, upload_dir, extension)
    asset = MediaAsset(
        uploaded_by=current_admin.id,
        object_key=object_key,
        original_filename=(file.filename or "")[:255] or None,
        mime_type=mime_type,
        size_bytes=len(normalized),
        checksum_sha256=checksum,
        status=MediaStatus.READY,
        alt_text=None,
    )
    try:
        db.add(asset)
        db.commit()
        db.refresh(asset)
    except Exception:
        db.rollback()
        try:
            os.remove(os.path.join(upload_dir, object_key))
        except OSError:
            pass
        raise

    return ImageUploadResponse(
        id=asset.id,
        object_key=asset.object_key,
        mime_type=asset.mime_type,
        size_bytes=asset.size_bytes,
        checksum_sha256=asset.checksum_sha256,
        status=asset.status,
        url=f"/media/{asset.object_key}",
    )
