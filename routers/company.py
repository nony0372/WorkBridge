from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.notification_service import get_unread_notifications

router = APIRouter(prefix="/company", tags=["company"])
templates = Jinja2Templates(directory="templates")


@router.get("/setup", response_class=HTMLResponse)
async def company_setup_page(request: Request, user=Depends(require_role("hr")), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "company_setup.html", {
        "request": request, "user": user, "company": company,
        "notifications": notifications
    })


@router.post("/setup")
async def company_setup(
    request: Request,
    name: str = Form(...),
    industry: str = Form(""),
    city: str = Form(""),
    description: str = Form(""),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if company:
        company.name = name
        company.industry = industry
        company.city = city
        company.description = description
    else:
        company = models.Company(
            name=name, industry=industry, city=city,
            description=description, hr_user_id=user.id
        )
        db.add(company)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/{company_id}", response_class=HTMLResponse)
async def company_detail(
    company_id: int,
    request: Request,
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
    vacancies = db.query(models.Vacancy).filter(
        models.Vacancy.company_id == company_id,
        models.Vacancy.is_active == True
    ).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "company_detail.html", {
        "request": request, "user": user, "company": company,
        "reviews": reviews, "avg_rating": avg_rating, "vacancies": vacancies,
        "notifications": notifications
    })
