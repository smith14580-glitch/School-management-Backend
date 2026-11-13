from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import PromotionLog, Student, StudentEnrollment, SchoolClass, AcademicSession, ActivityLog

promotion_router = APIRouter(prefix="/api/promotion", tags=["promotion"])
reports_router = APIRouter(prefix="/api/reports", tags=["reports"])
activity_router = APIRouter(prefix="/api/activity-log", tags=["activity"])
backup_router = APIRouter(prefix="/api/backup", tags=["backup"])
whatsapp_router = APIRouter(prefix="/api/whatsapp", tags=["whatsapp"])


class PromoteIn(BaseModel):
    from_class_id: int
    to_class_id: Optional[int] = None
    session_id: Optional[int] = None
    student_ids: List[int] = []
    action: str = "promoted"


@promotion_router.get("")
def index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("promotion.manage")(user, db)
    classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).order_by(SchoolClass.class_order).all()
    return [{"id": c.id, "name": c.name, "section": c.section, "is_final_year": c.is_final_year} for c in classes]


@promotion_router.get("/classes/{class_id}")
def class_show(class_id: int, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("promotion.manage")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    enrs = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == class_id, StudentEnrollment.academic_session_id == session_id, StudentEnrollment.status == "active").all()
    out = []
    for e in enrs:
        st = db.get(Student, e.student_id)
        out.append({"student_id": st.id, "name": st.name, "roll_number": e.roll_number, "enrollment_id": e.id})
    return out


@promotion_router.post("/classes/{class_id}/transfer")
def class_transfer(class_id: int, to_class_id: Optional[int] = None, student_ids: List[int] = [], user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("promotion.manage")(user, db)
    cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
    sess_id = cs.id if cs else 1
    cls = db.get(SchoolClass, class_id)
    is_final = cls.is_final_year if cls else False
    for sid in student_ids:
        enr = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == sid, StudentEnrollment.class_id == class_id, StudentEnrollment.academic_session_id == sess_id, StudentEnrollment.status == "active").first()
        if not enr:
            continue
        enr.status = "promoted" if not is_final else "graduated"
        enr.ended_on = date.today()
        action = "graduated" if is_final else "promoted"
        if to_class_id and not is_final:
            # create new enrollment next session
            next_sess = db.query(AcademicSession).filter(AcademicSession.id != sess_id).first()
            ns = next_sess.id if next_sess else sess_id
            roll = 1
            existing = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == to_class_id, StudentEnrollment.academic_session_id == ns).all()
            used = {x.roll_number for x in existing}
            while roll in used:
                roll += 1
            db.add(StudentEnrollment(student_id=sid, class_id=to_class_id, academic_session_id=ns, roll_number=roll, status="active", enrolled_on=date.today()))
        st = db.get(Student, sid)
        if st and is_final:
            st.status = "graduated"
        db.add(PromotionLog(student_id=sid, from_class_id=class_id, to_class_id=to_class_id, from_session_id=sess_id,
                            to_session_id=(sess_id if not to_class_id else sess_id), action=action, performed_by=user.id))
    db.commit()
    return {"ok": True}


@promotion_router.post("/run")
def run_promotion(data: PromoteIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("promotion.manage")(user, db)
    return {"ok": True}


# reports
@reports_router.get("")
def reports_index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("reports.view")(user, db)
    return {"ok": True}


@reports_router.get("/students/{student_id}/weekly")
def weekly(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("reports.view")(user, db)
    from datetime import timedelta
    today = date.today()
    week_ago = today - timedelta(days=7)
    att = db.query(__import__("app.models", fromlist=["Attendance"]).Attendance).filter(
        __import__("app.models", fromlist=["Attendance"]).Attendance.student_id == student_id,
        __import__("app.models", fromlist=["Attendance"]).Attendance.date >= week_ago).all()
    tests = db.query(__import__("app.models", fromlist=["DailyTestMark"]).DailyTestMark).join(
        __import__("app.models", fromlist=["DailyTest"]).DailyTest).filter(
        __import__("app.models", fromlist=["DailyTestMark"]).DailyTestMark.student_id == student_id).all()
    st = db.get(Student, student_id)
    return {"student": {"id": st.id, "name": st.name} if st else None,
            "attendance": [{"date": str(a.date), "status": a.status} for a in att],
            "tests": [{"marks": (float(t.marks_obtained) if t.marks_obtained is not None else None)} for t in tests]}


@reports_router.get("/students/{student_id}/monthly")
def monthly(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("reports.view")(user, db)
    from datetime import timedelta
    today = date.today()
    month_ago = today - timedelta(days=30)
    att = db.query(__import__("app.models", fromlist=["Attendance"]).Attendance).filter(
        __import__("app.models", fromlist=["Attendance"]).Attendance.student_id == student_id,
        __import__("app.models", fromlist=["Attendance"]).Attendance.date >= month_ago).all()
    st = db.get(Student, student_id)
    return {"student": {"id": st.id, "name": st.name} if st else None,
            "attendance": [{"date": str(a.date), "status": a.status} for a in att]}


# activity log
@activity_router.get("")
def list_activity(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("activitylog.view")(user, db)
    rows = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(200).all()
    return [{"id": r.id, "user_id": r.user_id, "action": r.action, "target_table": r.target_table,
             "target_id": r.target_id, "description": r.description, "created_at": str(r.created_at)} for r in rows]


# backup
@backup_router.get("")
def backup_index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("backup.manage")(user, db)
    return {"ok": True}


@backup_router.get("/export/students")
def export_students(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("backup.manage")(user, db)
    students = db.query(Student).all()
    return [{"id": s.id, "student_code": s.student_code, "name": s.name, "status": s.status} for s in students]


@backup_router.get("/export/fees")
def export_fees(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("backup.manage")(user, db)
    recs = db.query(__import__("app.models", fromlist=["FeeRecord"]).FeeRecord).all()
    return [{"id": r.id, "student_id": r.student_id, "amount_due": float(r.amount_due or 0), "amount_paid": float(r.amount_paid or 0), "status": r.status} for r in recs]


@backup_router.get("/export/results")
def export_results(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("backup.manage")(user, db)
    recs = db.query(__import__("app.models", fromlist=["ExamResultSummary"]).ExamResultSummary).all()
    return [{"exam_id": r.exam_id, "student_id": r.student_id, "percentage": float(r.percentage or 0), "grade": r.grade} for r in recs]


# whatsapp (stub returning links)
@whatsapp_router.get("")
def wa_index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("whatsapp.send")(user, db)
    return {"ok": True}


@whatsapp_router.get("/students/{student_id}/weekly")
def wa_weekly(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("whatsapp.send")(user, db)
    st = db.get(Student, student_id)
    return {"student": st.name if st else None, "link": f"https://wa.me/?text=Weekly report for {st.name if st else ''}"}


@whatsapp_router.get("/students/{student_id}/monthly")
def wa_monthly(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("whatsapp.send")(user, db)
    st = db.get(Student, student_id)
    return {"student": st.name if st else None, "link": f"https://wa.me/?text=Monthly report for {st.name if st else ''}"}


@whatsapp_router.get("/students/{student_id}/fees")
def wa_fees(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("whatsapp.send")(user, db)
    st = db.get(Student, student_id)
    return {"link": f"https://wa.me/?text=Fee reminder for {st.name if st else ''}"}


@whatsapp_router.get("/exams/{exam_id}/students/{student_id}")
def wa_exam(exam_id: int, student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("whatsapp.send")(user, db)
    st = db.get(Student, student_id)
    return {"link": f"https://wa.me/?text=Exam result for {st.name if st else ''}"}
