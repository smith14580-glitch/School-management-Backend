import os
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.scoping import teacher_class_ids
from app.models import Student, StudentEnrollment, StudentDocument, AcademicSession, SchoolClass

router = APIRouter(prefix="/api/students", tags=["students"])


class StudentIn(BaseModel):
    name: str
    father_guardian_name: str
    dob: Optional[date] = None
    gender: Optional[str] = None
    contact: Optional[str] = None
    whatsapp_number: Optional[str] = None
    address: Optional[str] = None
    previous_school: Optional[str] = None
    admission_date: Optional[date] = None
    status: str = "active"
    # enrollment
    class_id: int
    academic_session_id: Optional[int] = None
    roll_number: Optional[int] = None


def student_code(db: Session) -> str:
    sess = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
    yr = (sess.year_label or "00")[:2] if sess else "00"
    # use last two of start year
    try:
        yr = sess.year_label.split("-")[0][-2:]
    except Exception:
        yr = "00"
    cnt = db.query(Student).count() + 1
    return f"SCH-{yr}-{cnt:04d}"


def student_out(s: Student, enrollment: StudentEnrollment | None = None):
    d = {
        "id": s.id, "student_code": s.student_code, "name": s.name,
        "father_guardian_name": s.father_guardian_name, "dob": str(s.dob) if s.dob else None,
        "gender": s.gender, "contact": s.contact, "whatsapp_number": s.whatsapp_number,
        "address": s.address, "previous_school": s.previous_school, "photo_path": s.photo_path,
        "admission_date": str(s.admission_date) if s.admission_date else None, "status": s.status,
    }
    if enrollment:
        d["enrollment_id"] = enrollment.id
        d["class_id"] = enrollment.class_id
        d["roll_number"] = enrollment.roll_number
        d["academic_session_id"] = enrollment.academic_session_id
        d["enrollment_status"] = enrollment.status
    return d


@router.get("")
def list_students(class_id: Optional[int] = None, session_id: Optional[int] = None,
                  q: Optional[str] = None, status: Optional[str] = None,
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.view")(user, db)
    ids = teacher_class_ids(user, db)
    # base students
    query = db.query(Student)
    if q:
        query = query.filter((Student.name.ilike(f"%{q}%")) | (Student.student_code.ilike(f"%{q}%")))
    if status:
        query = query.filter(Student.status == status)
    students = query.order_by(Student.name).all()
    # filter by class enrollment
    out = []
    for s in students:
        enroll_q = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == s.id)
        if class_id:
            enroll_q = enroll_q.filter(StudentEnrollment.class_id == class_id)
        if session_id:
            enroll_q = enroll_q.filter(StudentEnrollment.academic_session_id == session_id)
        enrs = enroll_q.all()
        if (class_id or session_id) and not enrs:
            continue
        if ids is not None and enrs:
            if not any(e.class_id in ids for e in enrs):
                continue
        if ids is not None and not enrs:
            # teacher with no enrollment filter? skip unknown
            continue
        enr = enrs[0] if enrs else None
        out.append(student_out(s, enr))
    return out


@router.get("/lookup")
def lookup(q: Optional[str] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("studentrecord.view")(user, db)
    query = db.query(Student)
    if q:
        query = query.filter((Student.name.ilike(f"%{q}%")) | (Student.student_code.ilike(f"%{q}%")))
    return [student_out(s) for s in query.limit(50).all()]


@router.get("/{student_id}")
def get_student(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.view")(user, db)
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404)
    enr = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == student_id).order_by(StudentEnrollment.id.desc()).first()
    return student_out(s, enr)


@router.post("")
def create_student(data: StudentIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.manage")(user, db)
    sess_id = data.academic_session_id
    if not sess_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        sess_id = cs.id if cs else 1
    # roll number
    roll = data.roll_number
    if roll is None:
        existing = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == data.class_id, StudentEnrollment.academic_session_id == sess_id).all()
        used = {e.roll_number for e in existing}
        roll = 1
        while roll in used:
            roll += 1
    s = Student(
        student_code=student_code(db), name=data.name, father_guardian_name=data.father_guardian_name,
        dob=data.dob, gender=data.gender, contact=data.contact, whatsapp_number=data.whatsapp_number,
        address=data.address, previous_school=data.previous_school, admission_date=data.admission_date,
        status=data.status,
    )
    db.add(s); db.flush()
    enr = StudentEnrollment(student_id=s.id, class_id=data.class_id, academic_session_id=sess_id,
                            roll_number=roll, status="active", enrolled_on=data.admission_date or date.today())
    db.add(enr); db.commit(); db.refresh(s)
    return student_out(s, enr)


@router.post("/{student_id}")
def update_student(student_id: int, data: StudentIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.manage")(user, db)
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404)
    for field in ["name","father_guardian_name","dob","gender","contact","whatsapp_number","address","previous_school","admission_date","status"]:
        setattr(s, field, getattr(data, field))
    db.commit(); db.refresh(s)
    enr = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == student_id).order_by(StudentEnrollment.id.desc()).first()
    return student_out(s, enr)


@router.post("/{student_id}/status")
def toggle_student(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.manage")(user, db)
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404)
    s.status = "inactive" if s.status == "active" else "active"
    db.commit()
    return {"status": s.status}


@router.get("/{student_id}/id-card")
def id_card(student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.view")(user, db)
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(404)
    enr = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == student_id).order_by(StudentEnrollment.id.desc()).first()
    cls = db.get(SchoolClass, enr.class_id) if enr else None
    sess = db.get(AcademicSession, enr.academic_session_id) if enr else None
    setting = lambda k, d=None: (db.query(__import__("app.models", fromlist=["Setting"]).Setting).filter(__import__("app.models", fromlist=["Setting"]).Setting.setting_key == k).first())
    from app.models import Setting
    def get_setting(k):
        r = db.query(Setting).filter(Setting.setting_key == k).first()
        return r.setting_value if r else None
    return {
        "student": student_out(s, enr),
        "class": {"name": cls.name, "section": cls.section} if cls else None,
        "session": sess.year_label if sess else None,
        "school_name": get_setting("school_name"),
    }
