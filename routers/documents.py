import os
import uuid
from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie
import models
from services.notification_service import get_unread_notifications

router = APIRouter(prefix="/documents", tags=["documents"])
templates = Jinja2Templates(directory="templates")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png"}


@router.get("/", response_class=HTMLResponse)
async def documents_list(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    docs = db.query(models.Document).filter(models.Document.user_id == user.id).order_by(
        models.Document.uploaded_at.desc()
    ).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "documents.html", {
        "request": request, "user": user, "documents": docs,
        "notifications": notifications
    })


@router.post("/upload")
async def upload_document(
    request: Request,
    category: str = Form("other"),
    file: UploadFile = File(...),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return RedirectResponse(url="/documents/?error=invalid_type", status_code=302)

    user_dir = os.path.join(UPLOAD_DIR, f"user_{user.id}")
    os.makedirs(user_dir, exist_ok=True)

    unique_name = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(user_dir, unique_name)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    doc = models.Document(
        user_id=user.id,
        filename=unique_name,
        original_filename=file.filename,
        category=category,
        filepath=filepath
    )
    db.add(doc)
    db.commit()
    return RedirectResponse(url="/documents/", status_code=302)


@router.get("/download/{doc_id}")
async def download_document(doc_id: int, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == user.id
    ).first()
    if not doc or not os.path.exists(doc.filepath):
        return RedirectResponse(url="/documents/", status_code=302)
    return FileResponse(doc.filepath, filename=doc.original_filename)


@router.post("/delete/{doc_id}")
async def delete_document(doc_id: int, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    doc = db.query(models.Document).filter(
        models.Document.id == doc_id,
        models.Document.user_id == user.id
    ).first()
    if doc:
        if os.path.exists(doc.filepath):
            os.remove(doc.filepath)
        db.delete(doc)
        db.commit()
    return RedirectResponse(url="/documents/", status_code=302)
