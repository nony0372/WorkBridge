"""
Seed script for WorkBridge MVP.
Creates test data: 1 company, 1 HR user, 2 employees, 5 vacancies.
Run: python seed.py
"""
import os
import sys

# Ensure we can import from the project
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal, Base
import models
from auth import get_password_hash

# Create all tables
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    # Check if data already exists
    if db.query(models.User).first():
        print("[!] Dannye uzhe sushchestvuyut. Ochistite BD ili propustite.")
        sys.exit(0)

    # 1. Create HR user
    hr_user = models.User(
        email="hr@workbridge.kz",
        password_hash=get_password_hash("password123"),
        role="hr",
        full_name="Алия Нурланова"
    )
    db.add(hr_user)
    db.flush()

    # 2. Create company
    company = models.Company(
        name="TechBridge KZ",
        industry="Информационные технологии",
        city="Алматы",
        description="Ведущая IT-компания Казахстана, специализирующаяся на разработке корпоративных решений и мобильных приложений.",
        hr_user_id=hr_user.id
    )
    db.add(company)
    db.flush()

    # 3. Create employees
    emp1 = models.User(
        email="ivan@workbridge.kz",
        password_hash=get_password_hash("password123"),
        role="employee",
        full_name="Иван Петров"
    )
    db.add(emp1)
    db.flush()

    profile1 = models.EmployeeProfile(
        user_id=emp1.id,
        skills="Python, Django, FastAPI, PostgreSQL, Docker, Git",
        experience_years=4,
        desired_salary=800000,
        city="Алматы",
        bio="Backend-разработчик с 4-летним опытом в веб-разработке. Специализируюсь на Python и микросервисной архитектуре."
    )
    db.add(profile1)

    emp2 = models.User(
        email="anna@workbridge.kz",
        password_hash=get_password_hash("password123"),
        role="employee",
        full_name="Анна Сидорова"
    )
    db.add(emp2)
    db.flush()

    profile2 = models.EmployeeProfile(
        user_id=emp2.id,
        skills="React, TypeScript, Node.js, CSS, Figma, UI/UX",
        experience_years=3,
        desired_salary=700000,
        city="Астана",
        bio="Frontend-разработчик и дизайнер. Создаю красивые и удобные пользовательские интерфейсы."
    )
    db.add(profile2)

    # 4. Create vacancies
    vacancies_data = [
        {
            "title": "Senior Python Developer",
            "description": "Разработка и поддержка серверной части высоконагруженных приложений на Python. Проектирование API, работа с базами данных, оптимизация производительности.",
            "requirements": "Python 3.8+, FastAPI/Django, PostgreSQL, Docker, опыт от 3 лет",
            "salary_min": 700000, "salary_max": 1200000,
            "city": "Алматы", "employment_type": "full-time",
            "industry": "IT"
        },
        {
            "title": "Frontend React Developer",
            "description": "Создание пользовательских интерфейсов для веб-приложений с использованием React и TypeScript.",
            "requirements": "React, TypeScript, CSS/SASS, Git, опыт от 2 лет",
            "salary_min": 500000, "salary_max": 900000,
            "city": "Астана", "employment_type": "full-time",
            "industry": "IT"
        },
        {
            "title": "DevOps Engineer",
            "description": "Настройка и поддержка CI/CD, контейнеризация, мониторинг инфраструктуры, автоматизация развёртывания.",
            "requirements": "Linux, Docker, Kubernetes, CI/CD, AWS/GCP, Terraform",
            "salary_min": 800000, "salary_max": 1500000,
            "city": "Алматы", "employment_type": "full-time",
            "industry": "IT"
        },
        {
            "title": "QA Engineer (Remote)",
            "description": "Тестирование веб и мобильных приложений, написание автотестов, создание тест-планов.",
            "requirements": "Опыт ручного тестирования, Selenium/Cypress, SQL, API тестирование",
            "salary_min": 400000, "salary_max": 700000,
            "city": "Удалённо", "employment_type": "remote",
            "industry": "IT"
        },
        {
            "title": "UI/UX Designer",
            "description": "Проектирование пользовательских интерфейсов для мобильных и веб-приложений. Создание прототипов, дизайн-систем.",
            "requirements": "Figma, Adobe XD, знание принципов UX, портфолио обязательно",
            "salary_min": 450000, "salary_max": 800000,
            "city": "Алматы", "employment_type": "part-time",
            "industry": "Дизайн"
        }
    ]

    for v_data in vacancies_data:
        vacancy = models.Vacancy(company_id=company.id, **v_data)
        db.add(vacancy)

    db.commit()

    print("[OK] Test data created successfully!")
    print()
    print("Accounts (password: password123):")
    print(f"   HR:         hr@workbridge.kz")
    print(f"   Employee 1: ivan@workbridge.kz")
    print(f"   Employee 2: anna@workbridge.kz")
    print()
    print(f"   Company:    TechBridge KZ (Almaty)")
    print(f"   Vacancies:  5")

except Exception as e:
    db.rollback()
    print(f"[ERROR] {e}")
    raise
finally:
    db.close()
