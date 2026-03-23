from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.ai_service import match_jobs_for_employee, match_candidates_for_vacancy
from services.notification_service import get_unread_notifications

router = APIRouter(prefix="/ai", tags=["ai"])
templates = Jinja2Templates(directory="templates")


@router.get("/job-matching", response_class=HTMLResponse)
async def job_matching_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    profile = db.query(models.EmployeeProfile).filter(
        models.EmployeeProfile.user_id == user.id
    ).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "ai_job_matching.html", {
        "request": request, "user": user, "profile": profile,
        "notifications": notifications
    })


@router.post("/job-matching", response_class=HTMLResponse)
async def do_job_matching(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    profile = db.query(models.EmployeeProfile).filter(
        models.EmployeeProfile.user_id == user.id
    ).first()
    if not profile:
        return RedirectResponse(url="/profile", status_code=302)

    employee_data = {
        "full_name": user.full_name,
        "skills": profile.skills,
        "experience_years": profile.experience_years,
        "desired_salary": profile.desired_salary,
        "city": profile.city,
        "bio": profile.bio
    }

    vacancies = db.query(models.Vacancy).filter(models.Vacancy.is_active == True).all()
    vacancies_data = [{
        "vacancy_id": v.id,
        "title": v.title,
        "description": v.description,
        "requirements": v.requirements,
        "salary_min": v.salary_min,
        "salary_max": v.salary_max,
        "city": v.city,
        "employment_type": v.employment_type,
        "industry": v.industry
    } for v in vacancies]

    results = match_jobs_for_employee(employee_data, vacancies_data)

    # Enrich results with vacancy info
    vacancy_map = {v.id: v for v in vacancies}
    enriched = []
    for r in results:
        if "error" in r:
            enriched.append(r)
            continue
        vid = r.get("vacancy_id")
        v = vacancy_map.get(vid)
        if v:
            r["vacancy"] = v
            enriched.append(r)

    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "ai_job_matching.html", {
        "request": request, "user": user, "profile": profile,
        "results": enriched, "notifications": notifications
    })


@router.get("/candidate-search", response_class=HTMLResponse)
async def candidate_search_page(request: Request, user=Depends(require_role("hr")), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    vacancies = []
    if company:
        vacancies = db.query(models.Vacancy).filter(
            models.Vacancy.company_id == company.id
        ).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "ai_candidate_search.html", {
        "request": request, "user": user, "company": company,
        "vacancies": vacancies, "notifications": notifications
    })


@router.post("/candidate-search", response_class=HTMLResponse)
async def do_candidate_search(
    request: Request,
    vacancy_id: int = Form(...),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    vacancy = db.query(models.Vacancy).filter(models.Vacancy.id == vacancy_id).first()
    if not vacancy:
        return RedirectResponse(url="/ai/candidate-search", status_code=302)

    vacancy_data = {
        "title": vacancy.title,
        "description": vacancy.description,
        "requirements": vacancy.requirements,
        "salary_min": vacancy.salary_min,
        "salary_max": vacancy.salary_max,
        "city": vacancy.city,
        "employment_type": vacancy.employment_type,
    }

    profiles = db.query(models.EmployeeProfile).all()
    candidates_data = []
    user_map = {}
    for p in profiles:
        u = db.query(models.User).filter(models.User.id == p.user_id).first()
        if u:
            user_map[u.id] = u
            candidates_data.append({
                "candidate_id": u.id,
                "full_name": u.full_name,
                "skills": p.skills,
                "experience_years": p.experience_years,
                "desired_salary": p.desired_salary,
                "city": p.city,
                "bio": p.bio
            })

    results = match_candidates_for_vacancy(vacancy_data, candidates_data)

    enriched = []
    for r in results:
        if "error" in r:
            enriched.append(r)
            continue
        cid = r.get("candidate_id")
        u = user_map.get(cid)
        if u:
            r["candidate"] = u
            enriched.append(r)

    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    vacancies = db.query(models.Vacancy).filter(models.Vacancy.company_id == company.id).all() if company else []
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "ai_candidate_search.html", {
        "request": request, "user": user, "company": company,
        "vacancies": vacancies, "results": enriched,
        "selected_vacancy": vacancy, "notifications": notifications
    })
