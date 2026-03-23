from fastapi import APIRouter, Depends, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.notification_service import get_unread_notifications

router = APIRouter(prefix="/vacancies", tags=["vacancies"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def vacancies_list(
    request: Request,
    keyword: str = Query("", alias="q"),
    city: str = Query(""),
    salary_min: float = Query(0),
    salary_max: float = Query(0),
    employment_type: str = Query(""),
    industry: str = Query(""),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    query = db.query(models.Vacancy).filter(models.Vacancy.is_active == True)
    if keyword:
        query = query.filter(
            or_(
                models.Vacancy.title.ilike(f"%{keyword}%"),
                models.Vacancy.description.ilike(f"%{keyword}%"),
                models.Vacancy.requirements.ilike(f"%{keyword}%")
            )
        )
    if city:
        query = query.filter(models.Vacancy.city.ilike(f"%{city}%"))
    if salary_min > 0:
        query = query.filter(models.Vacancy.salary_max >= salary_min)
    if salary_max > 0:
        query = query.filter(models.Vacancy.salary_min <= salary_max)
    if employment_type:
        query = query.filter(models.Vacancy.employment_type == employment_type)
    if industry:
        query = query.filter(models.Vacancy.industry.ilike(f"%{industry}%"))

    vacancies = query.order_by(models.Vacancy.created_at.desc()).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "vacancies_list.html", {
        "request": request, "user": user, "vacancies": vacancies,
        "notifications": notifications,
        "filters": {
            "q": keyword, "city": city, "salary_min": salary_min,
            "salary_max": salary_max, "employment_type": employment_type,
            "industry": industry
        }
    })


@router.get("/create", response_class=HTMLResponse)
async def vacancy_create_page(request: Request, user=Depends(require_role("hr")), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "vacancy_form.html", {
        "request": request, "user": user, "company": company,
        "notifications": notifications
    })


@router.post("/create")
async def vacancy_create(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    requirements: str = Form(""),
    salary_min: float = Form(0),
    salary_max: float = Form(0),
    city: str = Form(""),
    employment_type: str = Form("full-time"),
    industry: str = Form(""),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    vacancy = models.Vacancy(
        company_id=company.id, title=title, description=description,
        requirements=requirements, salary_min=salary_min, salary_max=salary_max,
        city=city, employment_type=employment_type, industry=industry
    )
    db.add(vacancy)
    db.commit()
    return RedirectResponse(url="/vacancies/", status_code=302)


@router.get("/{vacancy_id}", response_class=HTMLResponse)
async def vacancy_detail(
    vacancy_id: int, request: Request,
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not vacancy:
        return RedirectResponse(url="/vacancies/", status_code=302)
    company = db.query(models.Company).filter(models.Company.id == vacancy.company_id).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "vacancy_detail.html", {
        "request": request, "user": user, "vacancy": vacancy, "company": company,
        "notifications": notifications
    })


@router.get("/{vacancy_id}/edit", response_class=HTMLResponse)
async def vacancy_edit_page(
    vacancy_id: int, request: Request,
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not vacancy:
        return RedirectResponse(url="/vacancies/", status_code=302)
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company or company.id != vacancy.company_id:
        return RedirectResponse(url="/vacancies/", status_code=302)
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "vacancy_form.html", {
        "request": request, "user": user, "company": company,
        "vacancy": vacancy, "notifications": notifications
    })


@router.post("/{vacancy_id}/edit")
async def vacancy_edit(
    vacancy_id: int,
    title: str = Form(...),
    description: str = Form(""),
    requirements: str = Form(""),
    salary_min: float = Form(0),
    salary_max: float = Form(0),
    city: str = Form(""),
    employment_type: str = Form("full-time"),
    industry: str = Form(""),
    is_active: bool = Form(True),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not vacancy:
        return RedirectResponse(url="/vacancies/", status_code=302)
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company or company.id != vacancy.company_id:
        return RedirectResponse(url="/vacancies/", status_code=302)
    vacancy.title = title
    vacancy.description = description
    vacancy.requirements = requirements
    vacancy.salary_min = salary_min
    vacancy.salary_max = salary_max
    vacancy.city = city
    vacancy.employment_type = employment_type
    vacancy.industry = industry
    vacancy.is_active = is_active
    db.commit()
    return RedirectResponse(url=f"/vacancies/{vacancy_id}", status_code=302)


@router.post("/{vacancy_id}/toggle")
async def vacancy_toggle(
    vacancy_id: int,
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if vacancy:
        company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
        if company and company.id == vacancy.company_id:
            vacancy.is_active = not vacancy.is_active
            db.commit()
    return RedirectResponse(url="/vacancies/", status_code=302)
