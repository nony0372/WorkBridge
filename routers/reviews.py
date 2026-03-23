from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.notification_service import get_unread_notifications

router = APIRouter(prefix="/reviews", tags=["reviews"])
templates = Jinja2Templates(directory="templates")


# ===== Company Reviews (by employees) =====

@router.get("/company/{company_id}", response_class=HTMLResponse)
async def company_reviews(
    company_id: int, request: Request,
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        return RedirectResponse(url="/dashboard", status_code=302)
    reviews = db.query(models.ReviewCompany).filter(
        models.ReviewCompany.company_id == company_id
    ).order_by(models.ReviewCompany.created_at.desc()).all()
    avg_rating = 0
    if reviews:
        avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 1)
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "reviews_company.html", {
        "request": request, "user": user, "company": company,
        "reviews": reviews, "avg_rating": avg_rating,
        "notifications": notifications
    })


@router.post("/company/{company_id}")
async def post_company_review(
    company_id: int,
    rating: int = Form(...),
    text: str = Form(""),
    is_anonymous: bool = Form(False),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    if rating < 1 or rating > 5:
        return RedirectResponse(url=f"/reviews/company/{company_id}", status_code=302)
    review = models.ReviewCompany(
        user_id=user.id, company_id=company_id,
        rating=rating, text=text, is_anonymous=is_anonymous
    )
    db.add(review)
    db.commit()
    return RedirectResponse(url=f"/reviews/company/{company_id}", status_code=302)


# ===== Employee Reviews (by HR) =====

@router.get("/employees", response_class=HTMLResponse)
async def employee_reviews_list(
    request: Request,
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    employees = db.query(models.User).filter(models.User.role == "employee").all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "reviews_employees.html", {
        "request": request, "user": user, "company": company,
        "employees": employees, "notifications": notifications
    })


@router.get("/employee/{employee_id}", response_class=HTMLResponse)
async def employee_review_detail(
    employee_id: int, request: Request,
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    employee = db.query(models.User).filter(models.User.id == employee_id).first()
    if not employee:
        return RedirectResponse(url="/reviews/employees", status_code=302)
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    reviews = db.query(models.ReviewEmployee).filter(
        models.ReviewEmployee.employee_id == employee_id
    ).order_by(models.ReviewEmployee.created_at.desc()).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "review_employee_detail.html", {
        "request": request, "user": user, "employee": employee,
        "company": company, "reviews": reviews,
        "notifications": notifications
    })


@router.post("/employee/{employee_id}")
async def post_employee_review(
    employee_id: int,
    productivity: int = Form(3),
    teamwork: int = Form(3),
    communication: int = Form(3),
    initiative: int = Form(3),
    notes: str = Form(""),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    review = models.ReviewEmployee(
        hr_user_id=user.id, employee_id=employee_id,
        company_id=company.id if company else None,
        productivity=productivity, teamwork=teamwork,
        communication=communication, initiative=initiative,
        notes=notes
    )
    db.add(review)
    db.commit()
    return RedirectResponse(url=f"/reviews/employee/{employee_id}", status_code=302)
