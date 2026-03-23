import io
import csv
import json
import datetime
from fastapi import APIRouter, Depends, Request, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.notification_service import get_unread_notifications
from services.ai_service import summarize_reports, generate_employment_contract
from services.pdf_service import generate_resume_pdf, generate_contract_pdf

router = APIRouter(tags=["reports"])
templates = Jinja2Templates(directory="templates")


# ===== HR Requests (leave, sick, dismissal) =====

@router.get("/hr-requests", response_class=HTMLResponse)
async def hr_requests_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    if user.role == "hr":
        company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
        requests_list = []
        if company:
            requests_list = db.query(models.HRRequest).filter(
                models.HRRequest.company_id == company.id
            ).order_by(models.HRRequest.created_at.desc()).all()
        for r in requests_list:
            r._user = db.query(models.User).filter(models.User.id == r.user_id).first()
        notifications = get_unread_notifications(db, user.id)
        return templates.TemplateResponse(request, "hr_requests_manage.html", {
            "request": request, "user": user, "company": company,
            "requests": requests_list, "notifications": notifications
        })
    else:
        my_requests = db.query(models.HRRequest).filter(
            models.HRRequest.user_id == user.id
        ).order_by(models.HRRequest.created_at.desc()).all()
        companies = db.query(models.Company).all()
        notifications = get_unread_notifications(db, user.id)
        return templates.TemplateResponse(request, "hr_requests.html", {
            "request": request, "user": user, "my_requests": my_requests,
            "companies": companies, "notifications": notifications
        })


@router.post("/hr-requests")
async def submit_hr_request(
    request: Request,
    request_type: str = Form(...),
    company_id: int = Form(...),
    start_date: str = Form(""),
    end_date: str = Form(""),
    reason: str = Form(""),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    hr_req = models.HRRequest(
        user_id=user.id, company_id=company_id,
        request_type=request_type,
        start_date=datetime.datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None,
        end_date=datetime.datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None,
        reason=reason
    )
    db.add(hr_req)
    db.commit()

    # Notify HR
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if company:
        from services.notification_service import create_notification
        type_names = {
            "leave": "отпуск", "sick": "больничный",
            "unpaid_leave": "отпуск без содержания", "dismissal": "увольнение"
        }
        create_notification(
            db, company.hr_user_id,
            f"Новое заявление: {type_names.get(request_type, request_type)}",
            f"Сотрудник {user.full_name} подал заявление на {type_names.get(request_type, request_type)}",
            "/hr-requests"
        )
    return RedirectResponse(url="/hr-requests", status_code=302)


@router.post("/hr-requests/{request_id}/status")
async def update_request_status(
    request_id: int,
    status: str = Form(...),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    hr_req = db.query(models.HRRequest).filter(models.HRRequest.id == request_id).first()
    if hr_req and status in ("approved", "rejected", "pending"):
        hr_req.status = status
        db.commit()
        status_names = {"approved": "одобрено", "rejected": "отклонено", "pending": "на рассмотрении"}
        from services.notification_service import create_notification
        create_notification(
            db, hr_req.user_id,
            f"Заявление {status_names.get(status, status)}",
            f"Ваше заявление было {status_names.get(status, status)}",
            "/hr-requests"
        )
    return RedirectResponse(url="/hr-requests", status_code=302)


# ===== Anonymous Messages =====

@router.get("/anonymous", response_class=HTMLResponse)
async def anonymous_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    companies = db.query(models.Company).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "anonymous.html", {
        "request": request, "user": user, "companies": companies,
        "notifications": notifications
    })


@router.post("/anonymous")
async def send_anonymous(
    company_id: int = Form(...),
    message: str = Form(...),
    db: Session = Depends(get_db)
):
    anon = models.AnonymousMessage(company_id=company_id, message=message)
    db.add(anon)
    db.commit()
    return RedirectResponse(url="/anonymous?sent=1", status_code=302)


# ===== Attendance =====

@router.get("/attendance", response_class=HTMLResponse)
async def attendance_page(
    request: Request,
    date: str = "",
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    records = db.query(models.Attendance).filter(
        models.Attendance.company_id == company.id,
        models.Attendance.date == target_date
    ).all()
    enriched = []
    for r in records:
        emp = db.query(models.User).filter(models.User.id == r.employee_id).first()
        enriched.append({"record": r, "employee_name": emp.full_name if emp else "N/A"})

    employees = db.query(models.User).filter(models.User.role == "employee").all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "attendance.html", {
        "request": request, "user": user, "company": company,
        "records": enriched, "date": date, "employees": employees,
        "notifications": notifications
    })


@router.post("/attendance")
async def mark_attendance(
    employee_id: int = Form(...),
    date: str = Form(...),
    arrived_at: str = Form(""),
    left_at: str = Form(""),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    existing = db.query(models.Attendance).filter(
        models.Attendance.employee_id == employee_id,
        models.Attendance.company_id == company.id,
        models.Attendance.date == target_date
    ).first()
    if existing:
        existing.arrived_at = arrived_at
        existing.left_at = left_at
    else:
        att = models.Attendance(
            employee_id=employee_id, company_id=company.id,
            date=target_date, arrived_at=arrived_at, left_at=left_at
        )
        db.add(att)
    db.commit()
    return RedirectResponse(url=f"/attendance?date={date}", status_code=302)


@router.get("/attendance/export/csv")
async def attendance_export_csv(
    date: str = "",
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    if not date:
        date = datetime.datetime.now().strftime("%Y-%m-%d")
    target_date = datetime.datetime.strptime(date, "%Y-%m-%d").date()
    records = db.query(models.Attendance).filter(
        models.Attendance.company_id == company.id,
        models.Attendance.date == target_date
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Сотрудник", "Дата", "Приход", "Уход"])
    for r in records:
        emp = db.query(models.User).filter(models.User.id == r.employee_id).first()
        writer.writerow([emp.full_name if emp else "N/A", str(r.date), r.arrived_at, r.left_at])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=attendance_{date}.csv"}
    )


# ===== Employee Reports =====

@router.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    notifications = get_unread_notifications(db, user.id)
    if user.role == "hr":
        company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
        reports = []
        if company:
            reports = db.query(models.EmployeeReport).filter(
                models.EmployeeReport.company_id == company.id
            ).order_by(models.EmployeeReport.submitted_at.desc()).all()
        for r in reports:
            r._user = db.query(models.User).filter(models.User.id == r.user_id).first()
        return templates.TemplateResponse(request, "reports_hr.html", {
            "request": request, "user": user, "company": company,
            "reports": reports, "notifications": notifications
        })
    else:
        my_reports = db.query(models.EmployeeReport).filter(
            models.EmployeeReport.user_id == user.id
        ).order_by(models.EmployeeReport.submitted_at.desc()).all()
        companies = db.query(models.Company).all()
        return templates.TemplateResponse(request, "reports_employee.html", {
            "request": request, "user": user, "my_reports": my_reports,
            "companies": companies, "notifications": notifications
        })


@router.post("/reports")
async def submit_report(
    company_id: int = Form(...),
    period: str = Form(...),
    tasks_done: str = Form(""),
    blockers: str = Form(""),
    plans: str = Form(""),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    report = models.EmployeeReport(
        user_id=user.id, company_id=company_id, period=period,
        tasks_done=tasks_done, blockers=blockers, plans=plans
    )
    db.add(report)
    db.commit()
    return RedirectResponse(url="/reports", status_code=302)


@router.post("/reports/summarize", response_class=HTMLResponse)
async def summarize_team_reports(
    request: Request,
    period: str = Form(""),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    query = db.query(models.EmployeeReport)
    if company:
        query = query.filter(models.EmployeeReport.company_id == company.id)
    if period:
        query = query.filter(models.EmployeeReport.period == period)
    reports = query.all()

    reports_data = [{
        "employee": db.query(models.User).filter(models.User.id == r.user_id).first().full_name if db.query(models.User).filter(models.User.id == r.user_id).first() else "N/A",
        "period": r.period,
        "tasks_done": r.tasks_done,
        "blockers": r.blockers,
        "plans": r.plans
    } for r in reports]

    summary = summarize_reports(reports_data)

    for r in reports:
        r._user = db.query(models.User).filter(models.User.id == r.user_id).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "reports_hr.html", {
        "request": request, "user": user, "company": company,
        "reports": reports, "ai_summary": summary,
        "notifications": notifications
    })


# ===== Resume Builder =====

@router.get("/resume", response_class=HTMLResponse)
async def resume_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    resumes = db.query(models.Resume).filter(
        models.Resume.user_id == user.id
    ).order_by(models.Resume.created_at.desc()).all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "resume.html", {
        "request": request, "user": user, "resumes": resumes,
        "notifications": notifications
    })


@router.get("/resume/create", response_class=HTMLResponse)
async def resume_create_page(request: Request, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "resume_form.html", {
        "request": request, "user": user, "notifications": notifications
    })


@router.post("/resume/create")
async def resume_create(
    request: Request,
    title: str = Form("Резюме"),
    full_name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    city: str = Form(""),
    bio: str = Form(""),
    skills: str = Form(""),
    languages: str = Form(""),
    experience_json: str = Form("[]"),
    education_json: str = Form("[]"),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    try:
        experience = json.loads(experience_json)
    except Exception:
        experience = []
    try:
        education = json.loads(education_json)
    except Exception:
        education = []

    content = {
        "full_name": full_name or user.full_name,
        "email": email or user.email,
        "phone": phone,
        "city": city,
        "bio": bio,
        "skills": skills,
        "languages": languages,
        "experience": experience,
        "education": education
    }
    resume = models.Resume(
        user_id=user.id, title=title, content_json=content
    )
    db.add(resume)
    db.commit()
    return RedirectResponse(url="/resume", status_code=302)


@router.get("/resume/download/{resume_id}")
async def resume_download(resume_id: int, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    resume = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if not resume:
        return RedirectResponse(url="/resume", status_code=302)
    pdf_bytes = generate_resume_pdf(resume.content_json)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=resume_{resume_id}.pdf"}
    )


@router.post("/resume/delete/{resume_id}")
async def resume_delete(resume_id: int, user=Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    resume = db.query(models.Resume).filter(
        models.Resume.id == resume_id,
        models.Resume.user_id == user.id
    ).first()
    if resume:
        db.delete(resume)
        db.commit()
    return RedirectResponse(url="/resume", status_code=302)


# ===== Contract Generator =====

@router.get("/contract", response_class=HTMLResponse)
async def contract_page(request: Request, user=Depends(require_role("hr")), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "contract.html", {
        "request": request, "user": user, "company": company,
        "notifications": notifications
    })


@router.post("/contract/generate")
async def contract_generate(
    request: Request,
    employee_name: str = Form(...),
    position: str = Form(...),
    salary: float = Form(...),
    start_date: str = Form(...),
    probation_months: int = Form(0),
    working_hours: str = Form("9:00-18:00"),
    language: str = Form("ru"),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    contract_data = {
        "employee_name": employee_name,
        "position": position,
        "salary": salary,
        "start_date": start_date,
        "probation_months": probation_months,
        "working_hours": working_hours,
        "language": "русский" if language == "ru" else "казахский",
        "company_name": company.name if company else "",
        "city": company.city if company else ""
    }

    contract_text = generate_employment_contract(contract_data)
    pdf_bytes = generate_contract_pdf(contract_text, contract_data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=contract_{employee_name}.pdf"}
    )


# ===== Employee Analytics =====

@router.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, user=Depends(require_role("hr")), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)

    employees = db.query(models.User).filter(models.User.role == "employee").all()
    analytics_data = []
    for emp in employees:
        # Attendance
        total_days = db.query(models.Attendance).filter(
            models.Attendance.employee_id == emp.id,
            models.Attendance.company_id == company.id
        ).count()

        # Reviews
        reviews = db.query(models.ReviewEmployee).filter(
            models.ReviewEmployee.employee_id == emp.id
        ).all()
        avg_score = 0
        if reviews:
            scores = [(r.productivity + r.teamwork + r.communication + r.initiative) / 4 for r in reviews]
            avg_score = round(sum(scores) / len(scores), 1)

        # Requests count
        requests_count = db.query(models.HRRequest).filter(
            models.HRRequest.user_id == emp.id,
            models.HRRequest.company_id == company.id
        ).count()

        analytics_data.append({
            "employee": emp,
            "attendance_days": total_days,
            "avg_score": avg_score,
            "requests_count": requests_count
        })

    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "analytics.html", {
        "request": request, "user": user, "company": company,
        "analytics": analytics_data, "notifications": notifications
    })
