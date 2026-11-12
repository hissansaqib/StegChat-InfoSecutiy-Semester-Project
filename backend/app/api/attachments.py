"""Attachments storage and download router with SHA-256 integrity checks."""

import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Response
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import uuid

from ..db.session import get_db
from ..db.models import Attachment, ConversationMember, User
from ..auth.dependencies import get_current_user
from ..integrity import compute_sha256, verify_digest
from ..core.upload_validation import validate_upload

router = APIRouter(tags=["attachments"])

UPLOAD_STORAGE_DIR = os.path.abspath(os.getenv("UPLOAD_DIR", "uploads"))
os.makedirs(UPLOAD_STORAGE_DIR, exist_ok=True)

@router.post("/conversations/{conversation_id}/attachments")
async def upload_attachment(
    conversation_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify membership
    mem = db.query(ConversationMember).filter(
        ConversationMember.conversation_id == conversation_id,
        ConversationMember.user_id == current_user.id,
    ).first()
    if not mem:
        raise HTTPException(status_code=403, detail="Not a member of this conversation")

    raw_data = await file.read()
    try:
        safe_name, storage_name, detected_mime = validate_upload(raw_data, file.filename or "upload")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Compute authoritative SHA-256 on upload
    digest_sha256 = compute_sha256(raw_data)
    target_disk_path = os.path.join(UPLOAD_STORAGE_DIR, storage_name)

    with open(target_disk_path, "wb") as f:
        f.write(raw_data)

    attachment_id = str(uuid.uuid4())
    attachment = Attachment(
        id=attachment_id,
        conversation_id=conversation_id,
        uploader_id=current_user.id,
        filename=safe_name,
        mime_type=detected_mime,
        sha256=digest_sha256,
        size=len(raw_data),
        storage_path=target_disk_path,
    )
    db.add(attachment)
    db.commit()

    return {
        "id": attachment_id,
        "filename": safe_name,
        "size": len(raw_data),
        "sha256": digest_sha256,
        "mime_type": detected_mime,
    }

@router.get("/attachments/{attachment_id}")
def download_attachment(
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Verify user has access to this conversation
    mem = db.query(ConversationMember).filter(
        ConversationMember.conversation_id == attachment.conversation_id,
        ConversationMember.user_id == current_user.id,
    ).first()
    if not mem:
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this conversation")

    if not os.path.exists(attachment.storage_path):
        raise HTTPException(status_code=404, detail="Attachment file missing from storage disk")

    # Read disk file and execute MANDATORY SHA-256 integrity verification
    with open(attachment.storage_path, "rb") as f:
        disk_data = f.read()

    actual_sha256 = compute_sha256(disk_data)

    if not verify_digest(attachment.sha256, actual_sha256):
        # Return Integrity Error (422 / 500)
        raise HTTPException(
            status_code=422,
            detail=f"INTEGRITY ERROR: Stored file hash mismatch! Expected {attachment.sha256}, actual on disk {actual_sha256}. File has been tampered with or corrupted on disk.",
        )

    return Response(
        content=disk_data,
        media_type=attachment.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{attachment.filename}"',
            "X-SHA256": attachment.sha256,
        },
    )

