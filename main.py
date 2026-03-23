import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from database import engine, Base
import models  # noqa: F401

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WorkBridge", description="HR Platform MVP")

# Static files
os.makedirs("static/uploads", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Import routers
from routers import auth as auth_router
from routers import employee as employee_router
from routers import company as company_router
from routers import vacancies as vacancies_router
from routers import ai_matching as ai_router
from routers import documents as documents_router
from routers import reviews as reviews_router
from routers import payroll as payroll_router
from routers import enps as enps_router
from routers import reports as reports_router

app.include_router(auth_router.router)
app.include_router(employee_router.router)
app.include_router(company_router.router)
app.include_router(vacancies_router.router)
app.include_router(ai_router.router)
app.include_router(documents_router.router)
app.include_router(reviews_router.router)
app.include_router(payroll_router.router)
app.include_router(enps_router.router)
app.include_router(reports_router.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login", status_code=302)


from fastapi.responses import PlainTextResponse
import traceback

@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    error_msg = traceback.format_exc()
    return PlainTextResponse(str(error_msg), status_code=500)

@app.exception_handler(307)
async def redirect_handler(request: Request, exc):
    return RedirectResponse(url="/auth/login", status_code=302)
