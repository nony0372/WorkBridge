from sqlalchemy.orm import Session
import models
import datetime


def create_notification(db: Session, user_id: int, title: str, message: str, link: str = ""):
    notification = models.Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
        created_at=datetime.datetime.utcnow()
    )
    db.add(notification)
    db.commit()
    return notification


def get_unread_notifications(db: Session, user_id: int):
    return db.query(models.Notification).filter(
        models.Notification.user_id == user_id,
        models.Notification.is_read == False
    ).order_by(models.Notification.created_at.desc()).all()


def get_all_notifications(db: Session, user_id: int, limit: int = 50):
    return db.query(models.Notification).filter(
        models.Notification.user_id == user_id
    ).order_by(models.Notification.created_at.desc()).limit(limit).all()


def mark_as_read(db: Session, notification_id: int, user_id: int):
    notif = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == user_id
    ).first()
    if notif:
        notif.is_read = True
        db.commit()
    return notif


def send_enps_notifications(db: Session, company_id: int, survey_id: int):
    """Send eNPS survey notifications to all employees associated with a company."""
    # Find all employees (for MVP, send to all employees)
    employees = db.query(models.User).filter(models.User.role == "employee").all()
    for emp in employees:
        create_notification(
            db, emp.id,
            "Опрос eNPS",
            "Пожалуйста, пройдите опрос eNPS и оцените вашу компанию как место работы.",
            f"/enps/respond/{survey_id}"
        )
