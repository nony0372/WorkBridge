from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.notification_service import get_unread_notifications

router = APIRouter(tags=["employee"])
templates = Jinja2Templates(directory="templates")


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    notifications = get_unread_notifications(db, user.id)
    if user.role == "hr":
        company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
        anon_messages = []
        if company:
            anon_messages = db.query(models.AnonymousMessage).filter(
                models.AnonymousMessage.company_id == company.id
            ).order_by(models.AnonymousMessage.created_at.desc()).limit(10).all()
        return templates.TemplateResponse(request, "dashboard_hr.html", {
            "user": user, "company": company,
            "notifications": notifications, "anon_messages": anon_messages
        })
    else:
        profile = db.query(models.EmployeeProfile).filter(
            models.EmployeeProfile.user_id == user.id
        ).first()
        return templates.TemplateResponse(request, "dashboard_employee.html", {
            "user": user, "profile": profile,
            "notifications": notifications
        })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    profile = db.query(models.EmployeeProfile).filter(
        models.EmployeeProfile.user_id == user.id
    ).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "profile.html", {
        "user": user, "profile": profile,
        "notifications": notifications
    })


@router.post("/profile")
async def update_profile(
    request: Request,
    skills: str = Form(""),
    experience_years: int = Form(0),
    desired_salary: float = Form(0),
    city: str = Form(""),
    bio: str = Form(""),
    full_name: str = Form(""),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if full_name:
        user.full_name = full_name
    profile = db.query(models.EmployeeProfile).filter(
        models.EmployeeProfile.user_id == user.id
    ).first()
    if not profile:
        profile = models.EmployeeProfile(user_id=user.id)
        db.add(profile)
    profile.skills = skills
    profile.experience_years = experience_years
    profile.desired_salary = desired_salary
    profile.city = city
    profile.bio = bio
    db.commit()
    return RedirectResponse(url="/profile", status_code=302)


@router.get("/advance-calculator", response_class=HTMLResponse)
async def advance_calculator_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "advance_calculator.html", {
        "request": request, "user": user, "notifications": notifications
    })


@router.post("/advance-calculator")
async def calculate_advance(
    request: Request,
    monthly_salary: float = Form(...),
    days_worked: int = Form(...),
    working_days: int = Form(22),
    advance_percent: float = Form(0.5),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    available_advance = (monthly_salary / working_days) * days_worked * advance_percent
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "advance_calculator.html", {
        "request": request, "user": user, "notifications": notifications,
        "result": round(available_advance, 2),
        "monthly_salary": monthly_salary,
        "days_worked": days_worked,
        "working_days": working_days,
        "advance_percent": advance_percent
    })


@router.post("/advance-request")
async def submit_advance_request(
    request: Request,
    amount: float = Form(...),
    salary: float = Form(0),
    days_worked: int = Form(0),
    advance_percent: float = Form(0),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    advance_req = models.AdvanceRequest(
        employee_id=user.id,
        amount=amount,
        salary=salary,
        days_worked=days_worked,
        advance_percent=advance_percent
    )
    db.add(advance_req)
    db.commit()
    return RedirectResponse(url="/advance-calculator?submitted=1", status_code=302)


@router.get("/notifications", response_class=HTMLResponse)
async def notifications_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    from services.notification_service import get_all_notifications
    all_notifs = get_all_notifications(db, user.id)
    unread = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "notifications.html", {
        "request": request, "user": user, "notifications": unread,
        "all_notifications": all_notifs
    })


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    from services.notification_service import mark_as_read
    mark_as_read(db, notification_id, user.id)
    return RedirectResponse(url="/notifications", status_code=302)
