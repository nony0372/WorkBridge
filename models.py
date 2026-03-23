import datetime
from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, Date, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # employee / hr
    full_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee_profile = relationship("EmployeeProfile", back_populates="user", uselist=False)
    documents = relationship("Document", back_populates="user")
    resumes = relationship("Resume", back_populates="user")
    hr_requests = relationship("HRRequest", back_populates="user")
    employee_reports = relationship("EmployeeReport", back_populates="user")
    advance_requests = relationship("AdvanceRequest", back_populates="employee")
    notifications = relationship("Notification", back_populates="user")


class EmployeeProfile(Base):
    __tablename__ = "employee_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    skills = Column(Text, default="")
    experience_years = Column(Integer, default=0)
    desired_salary = Column(Float, default=0)
    city = Column(String(255), default="")
    bio = Column(Text, default="")

    user = relationship("User", back_populates="employee_profile")


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    industry = Column(String(255), default="")
    city = Column(String(255), default="")
    description = Column(Text, default="")
    hr_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    hr_user = relationship("User")
    vacancies = relationship("Vacancy", back_populates="company")
    reviews = relationship("ReviewCompany", back_populates="company")
    anonymous_messages = relationship("AnonymousMessage", back_populates="company")
    enps_surveys = relationship("ENPSSurvey", back_populates="company")


class Vacancy(Base):
    __tablename__ = "vacancies"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, default="")
    requirements = Column(Text, default="")
    salary_min = Column(Float, default=0)
    salary_max = Column(Float, default=0)
    city = Column(String(255), default="")
    employment_type = Column(String(50), default="full-time")
    industry = Column(String(255), default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="vacancies")


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    category = Column(String(100), default="other")
    filepath = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="documents")


class Resume(Base):
    __tablename__ = "resumes"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="Резюме")
    content_json = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class ReviewCompany(Base):
    __tablename__ = "reviews_company"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    rating = Column(Integer, nullable=False)
    text = Column(Text, default="")
    is_anonymous = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User")
    company = relationship("Company", back_populates="reviews")


class ReviewEmployee(Base):
    __tablename__ = "reviews_employee"
    id = Column(Integer, primary_key=True, index=True)
    hr_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    productivity = Column(Integer, default=3)
    teamwork = Column(Integer, default=3)
    communication = Column(Integer, default=3)
    initiative = Column(Integer, default=3)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    hr_user = relationship("User", foreign_keys=[hr_user_id])
    employee = relationship("User", foreign_keys=[employee_id])
    company = relationship("Company")


class HRRequest(Base):
    __tablename__ = "hr_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    request_type = Column(String(50), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    reason = Column(Text, default="")
    status = Column(String(20), default="pending")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="hr_requests")
    company = relationship("Company")


class AnonymousMessage(Base):
    __tablename__ = "anonymous_messages"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="anonymous_messages")


class Attendance(Base):
    __tablename__ = "attendance"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    date = Column(Date, nullable=False)
    arrived_at = Column(String(10), default="")
    left_at = Column(String(10), default="")

    employee = relationship("User")
    company = relationship("Company")


class ENPSSurvey(Base):
    __tablename__ = "enps_surveys"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    frequency = Column(String(20), default="monthly")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    company = relationship("Company", back_populates="enps_surveys")
    responses = relationship("ENPSResponse", back_populates="survey")


class ENPSResponse(Base):
    __tablename__ = "enps_responses"
    id = Column(Integer, primary_key=True, index=True)
    survey_id = Column(Integer, ForeignKey("enps_surveys.id"), nullable=False)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    score = Column(Integer, nullable=False)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    survey = relationship("ENPSSurvey", back_populates="responses")
    employee = relationship("User")


class Payroll(Base):
    __tablename__ = "payroll"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    month = Column(String(7), nullable=False)  # YYYY-MM
    base_salary = Column(Float, default=0)
    bonus = Column(Float, default=0)
    additional = Column(Float, default=0)
    deductions = Column(Float, default=0)
    advance = Column(Float, default=0)
    net_salary = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("User")
    company = relationship("Company")


class EmployeeReport(Base):
    __tablename__ = "employee_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    period = Column(String(20), nullable=False)
    tasks_done = Column(Text, default="")
    blockers = Column(Text, default="")
    plans = Column(Text, default="")
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="employee_reports")
    company = relationship("Company")


class AdvanceRequest(Base):
    __tablename__ = "advance_requests"
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    amount = Column(Float, nullable=False)
    salary = Column(Float, default=0)
    days_worked = Column(Integer, default=0)
    advance_percent = Column(Float, default=0)
    status = Column(String(20), default="pending")
    requested_at = Column(DateTime, default=datetime.datetime.utcnow)

    employee = relationship("User", back_populates="advance_requests")
    company = relationship("Company")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), default="")
    message = Column(Text, default="")
    link = Column(String(500), default="")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    user = relationship("User", back_populates="notifications")
