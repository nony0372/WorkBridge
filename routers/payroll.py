import io
import csv
import datetime
from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import require_role
import models
from services.notification_service import get_unread_notifications
from services.pdf_service import generate_payroll_pdf

router = APIRouter(prefix="/payroll", tags=["payroll"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def payroll_list(
    request: Request,
    month: str = "",
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    if not month:
        month = datetime.datetime.now().strftime("%Y-%m")
    payrolls = db.query(models.Payroll).filter(
        models.Payroll.company_id == company.id,
        models.Payroll.month == month
    ).all()

    enriched = []
    for p in payrolls:
        emp = db.query(models.User).filter(models.User.id == p.employee_id).first()
        enriched.append({
            "payroll": p,
            "employee_name": emp.full_name if emp else "Неизвестно"
        })

    employees = db.query(models.User).filter(models.User.role == "employee").all()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "payroll.html", {
        "request": request, "user": user, "company": company,
        "payrolls": enriched, "month": month, "employees": employees,
        "notifications": notifications
    })


@router.post("/add")
async def payroll_add(
    request: Request,
    employee_id: int = Form(...),
    month: str = Form(...),
    base_salary: float = Form(0),
    bonus: float = Form(0),
    additional: float = Form(0),
    deductions: float = Form(0),
    advance: float = Form(0),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    net_salary = base_salary + bonus + additional - deductions - advance
    payroll = models.Payroll(
        employee_id=employee_id, company_id=company.id, month=month,
        base_salary=base_salary, bonus=bonus, additional=additional,
        deductions=deductions, advance=advance, net_salary=net_salary
    )
    db.add(payroll)
    db.commit()
    return RedirectResponse(url=f"/payroll/?month={month}", status_code=302)


@router.get("/export/csv")
async def payroll_export_csv(
    month: str = "",
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    if not month:
        month = datetime.datetime.now().strftime("%Y-%m")
    payrolls = db.query(models.Payroll).filter(
        models.Payroll.company_id == company.id,
        models.Payroll.month == month
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Сотрудник", "Оклад", "Премия", "Доплаты", "Удержания", "Аванс", "К выплате"])
    for p in payrolls:
        emp = db.query(models.User).filter(models.User.id == p.employee_id).first()
        writer.writerow([
            emp.full_name if emp else "N/A",
            p.base_salary, p.bonus, p.additional, p.deductions, p.advance, p.net_salary
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=payroll_{month}.csv"}
    )


@router.get("/export/pdf")
async def payroll_export_pdf(
    month: str = "",
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    if not month:
        month = datetime.datetime.now().strftime("%Y-%m")
    payrolls = db.query(models.Payroll).filter(
        models.Payroll.company_id == company.id,
        models.Payroll.month == month
    ).all()

    data = []
    for p in payrolls:
        emp = db.query(models.User).filter(models.User.id == p.employee_id).first()
        data.append({
            "employee_name": emp.full_name if emp else "N/A",
            "base_salary": p.base_salary, "bonus": p.bonus,
            "additional": p.additional, "deductions": p.deductions,
            "advance": p.advance, "net_salary": p.net_salary
        })

    pdf_bytes = generate_payroll_pdf(data, company.name, month)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payroll_{month}.pdf"}
    )
