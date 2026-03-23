from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_password_hash, verify_password, create_access_token, get_optional_user
import models

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request, user=Depends(get_optional_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "register.html")


@router.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        return templates.TemplateResponse(request, "register.html", {
            "request": request, "error": "Пользователь с таким email уже существует"
        })
    if role not in ("employee", "hr"):
        return templates.TemplateResponse(request, "register.html", {
            "request": request, "error": "Неверная роль"
        })
    if len(password) < 6:
        return templates.TemplateResponse(request, "register.html", {
            "request": request, "error": "Пароль должен быть не менее 6 символов"
        })

    user = models.User(
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        full_name=full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if role == "employee":
        profile = models.EmployeeProfile(user_id=user.id)
        db.add(profile)
        db.commit()

    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, path="/")
    return response


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, user=Depends(get_optional_user)):
    if user:
        return RedirectResponse(url="/dashboard", status_code=302)
    return templates.TemplateResponse(request, "login.html")


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return templates.TemplateResponse(request, "login.html", {
            "request": request, "error": "Неверный email или пароль"
        })
    
    is_valid = verify_password(password, user.password_hash)
    if not is_valid:
        return templates.TemplateResponse(request, "login.html", {
            "request": request, "error": "Неверный email или пароль"
        })

    token = create_access_token({"sub": str(user.id)})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400, path="/")
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
