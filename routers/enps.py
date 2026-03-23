from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie, require_role
import models
from services.notification_service import get_unread_notifications, send_enps_notifications
from services.pdf_service import generate_enps_report_pdf

router = APIRouter(prefix="/enps", tags=["enps"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def enps_dashboard(request: Request, user=Depends(require_role("hr")), db: Session = Depends(get_db)):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    surveys = db.query(models.ENPSSurvey).filter(
        models.ENPSSurvey.company_id == company.id
    ).order_by(models.ENPSSurvey.created_at.desc()).all()

    survey_data = []
    for s in surveys:
        responses = db.query(models.ENPSResponse).filter(
            models.ENPSResponse.survey_id == s.id
        ).all()
        total = len(responses)
        if total > 0:
            promoters = len([r for r in responses if r.score >= 9])
            detractors = len([r for r in responses if r.score <= 6])
            enps_score = round((promoters / total - detractors / total) * 100)
        else:
            enps_score = 0
        survey_data.append({"survey": s, "total": total, "enps_score": enps_score})

    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "enps_dashboard.html", {
        "request": request, "user": user, "company": company,
        "survey_data": survey_data, "notifications": notifications
    })


@router.post("/create")
async def create_survey(
    request: Request,
    frequency: str = Form("monthly"),
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    company = db.query(models.Company).filter(models.Company.hr_user_id == user.id).first()
    if not company:
        return RedirectResponse(url="/company/setup", status_code=302)
    survey = models.ENPSSurvey(company_id=company.id, frequency=frequency)
    db.add(survey)
    db.commit()
    db.refresh(survey)
    send_enps_notifications(db, company.id, survey.id)
    return RedirectResponse(url="/enps/", status_code=302)


@router.get("/respond/{survey_id}", response_class=HTMLResponse)
async def respond_survey_page(
    survey_id: int, request: Request,
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    survey = db.query(models.ENPSSurvey).filter(models.ENPSSurvey.id == survey_id).first()
    if not survey:
        return RedirectResponse(url="/dashboard", status_code=302)
    company = db.query(models.Company).filter(models.Company.id == survey.company_id).first()
    existing = db.query(models.ENPSResponse).filter(
        models.ENPSResponse.survey_id == survey_id,
        models.ENPSResponse.employee_id == user.id
    ).first()
    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "enps_respond.html", {
        "request": request, "user": user, "survey": survey,
        "company": company, "existing": existing,
        "notifications": notifications
    })


@router.post("/respond/{survey_id}")
async def submit_response(
    survey_id: int,
    score: int = Form(...),
    comment: str = Form(""),
    user=Depends(get_current_user_from_cookie),
    db: Session = Depends(get_db)
):
    existing = db.query(models.ENPSResponse).filter(
        models.ENPSResponse.survey_id == survey_id,
        models.ENPSResponse.employee_id == user.id
    ).first()
    if existing:
        return RedirectResponse(url=f"/enps/respond/{survey_id}", status_code=302)
    resp = models.ENPSResponse(
        survey_id=survey_id, employee_id=user.id,
        score=score, comment=comment
    )
    db.add(resp)
    db.commit()
    return RedirectResponse(url="/dashboard", status_code=302)


@router.get("/analytics/{survey_id}", response_class=HTMLResponse)
async def enps_analytics(
    survey_id: int, request: Request,
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    survey = db.query(models.ENPSSurvey).filter(models.ENPSSurvey.id == survey_id).first()
    if not survey:
        return RedirectResponse(url="/enps/", status_code=302)
    company = db.query(models.Company).filter(models.Company.id == survey.company_id).first()
    responses = db.query(models.ENPSResponse).filter(
        models.ENPSResponse.survey_id == survey_id
    ).all()

    total = len(responses)
    promoters = passives = detractors = 0
    if total > 0:
        promoters = len([r for r in responses if r.score >= 9])
        passives = len([r for r in responses if 7 <= r.score <= 8])
        detractors = len([r for r in responses if r.score <= 6])
        enps_score = round((promoters / total - detractors / total) * 100)
        promoters_pct = round(promoters / total * 100)
        passives_pct = round(passives / total * 100)
        detractors_pct = round(detractors / total * 100)
    else:
        enps_score = promoters_pct = passives_pct = detractors_pct = 0

    all_surveys = db.query(models.ENPSSurvey).filter(
        models.ENPSSurvey.company_id == company.id
    ).order_by(models.ENPSSurvey.created_at).all()
    trend = []
    for s in all_surveys:
        resps = db.query(models.ENPSResponse).filter(
            models.ENPSResponse.survey_id == s.id
        ).all()
        t = len(resps)
        if t > 0:
            p = len([r for r in resps if r.score >= 9])
            d = len([r for r in resps if r.score <= 6])
            score = round((p / t - d / t) * 100)
        else:
            score = 0
        trend.append({"date": s.created_at.strftime("%Y-%m-%d"), "score": score})

    notifications = get_unread_notifications(db, user.id)
    return templates.TemplateResponse(request, "enps_analytics.html", {
        "request": request, "user": user, "company": company,
        "survey": survey, "responses": responses,
        "total": total, "enps_score": enps_score,
        "promoters_pct": promoters_pct, "passives_pct": passives_pct,
        "detractors_pct": detractors_pct, "trend": trend,
        "notifications": notifications
    })


@router.get("/export/{survey_id}/pdf")
async def enps_export_pdf(
    survey_id: int,
    user=Depends(require_role("hr")),
    db: Session = Depends(get_db)
):
    survey = db.query(models.ENPSSurvey).filter(models.ENPSSurvey.id == survey_id).first()
    if not survey:
        return RedirectResponse(url="/enps/", status_code=302)
    company = db.query(models.Company).filter(models.Company.id == survey.company_id).first()
    responses = db.query(models.ENPSResponse).filter(
        models.ENPSResponse.survey_id == survey_id
    ).all()
    total = len(responses)
    if total > 0:
        promoters = round(len([r for r in responses if r.score >= 9]) / total * 100)
        passives = round(len([r for r in responses if 7 <= r.score <= 8]) / total * 100)
        detractors = round(len([r for r in responses if r.score <= 6]) / total * 100)
        enps_score = promoters - detractors
    else:
        promoters = passives = detractors = enps_score = 0

    pdf_bytes = generate_enps_report_pdf({
        "company_name": company.name if company else "",
        "enps_score": enps_score,
        "total_responses": total,
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors
    })
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=enps_report_{survey_id}.pdf"}
    )
