from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import Student, Teacher, SchoolClass, Exam, FeeRecord, Attendance, Notice

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def dashboard_summary(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.view")(user, db)
    # counts
    students = db.query(Student).count()
    teachers = db.query(Teacher).count()
    classes = db.query(SchoolClass).count()
    exams = db.query(Exam).count()
    # fee summary
    fee = db.query(
        func.coalesce(func.sum(FeeRecord.amount_due), 0).label("total_due"),
        func.coalesce(func.sum(FeeRecord.amount_paid), 0).label("total_paid"),
    ).first()
    total_due = float(fee.total_due or 0)
    total_paid = float(fee.total_paid or 0)
    balance = total_due - total_paid
    # attendance today
    today = date.today()
    att = db.query(
        func.count(case((Attendance.status == "present", 1))).label("present"),
        func.count(case((Attendance.status == "absent", 1))).label("absent"),
    ).filter(Attendance.date == today).first()
    present = att.present or 0
    absent = att.absent or 0
    # upcoming exams
    upcoming = db.query(Exam).filter(Exam.status != "completed").order_by(Exam.start_date).limit(3).all()
    upcoming_list = [{"id": e.id, "name": e.name, "start_date": str(e.start_date), "status": e.status} for e in upcoming]
    # recent admissions
    recent = db.query(Student).order_by(Student.id.desc()).limit(3).all()
    recent_list = [{"id": s.id, "name": s.name, "student_code": s.student_code} for s in recent]
    # notices
    notices = db.query(Notice).filter(Notice.is_active == True).order_by(Notice.publish_at.desc()).limit(3).all()
    notices_list = [{"id": n.id, "title": n.title, "body": n.body} for n in notices]

    return {
        "students": students,
        "teachers": teachers,
        "classes": classes,
        "exams": exams,
        "fees": {"total_due": total_due, "total_paid": total_paid, "balance": balance},
        "attendance": {"present": present, "absent": absent},
        "upcoming_exams": upcoming_list,
        "recent_students": recent_list,
        "notices": notices_list,
    }
