from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.security import hash_password
from app.models import Teacher, TeacherAssignment, User, Role, AcademicSession, SchoolClass, Subject

router = APIRouter(prefix="/api/teachers", tags=["teachers"])


class TeacherIn(BaseModel):
    name: str
    contact: Optional[str] = None
    whatsapp_number: Optional[str] = None
    email: Optional[str] = None
    cnic: Optional[str] = None
    qualification: Optional[str] = None
    address: Optional[str] = None
    joining_date: Optional[date] = None
    basic_salary: float = 0
    status: str = "active"
    username: Optional[str] = None
    password: Optional[str] = None


def teacher_code(db: Session) -> str:
    cnt = db.query(Teacher).count() + 1
    return f"TCH-{cnt:04d}"


def teacher_out(t: Teacher):
    return {
        "id": t.id, "employee_code": t.employee_code, "name": t.name, "contact": t.contact,
        "whatsapp_number": t.whatsapp_number, "email": t.email, "cnic": t.cnic,
        "qualification": t.qualification, "address": t.address, "joining_date": str(t.joining_date) if t.joining_date else None,
        "basic_salary": float(t.basic_salary or 0), "status": t.status, "user_id": t.user_id,
    }


@router.get("")
def list_teachers(q: Optional[str] = None, status: Optional[str] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.view")(user, db)
    query = db.query(Teacher)
    if q:
        query = query.filter(Teacher.name.ilike(f"%{q}%"))
    if status:
        query = query.filter(Teacher.status == status)
    return [teacher_out(t) for t in query.order_by(Teacher.name).all()]


@router.get("/{teacher_id}")
def get_teacher(teacher_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.view")(user, db)
    t = db.get(Teacher, teacher_id)
    if not t:
        raise HTTPException(404)
    assigns = db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher_id).all()
    out = teacher_out(t)
    out["assignments"] = [{"id": a.id, "class_id": a.class_id, "subject_id": a.subject_id,
                           "academic_session_id": a.academic_session_id, "is_class_teacher": a.is_class_teacher} for a in assigns]
    return out


@router.post("")
def create_teacher(data: TeacherIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.manage")(user, db)
    user_id = None
    if data.username and data.password:
        role = db.query(Role).filter(Role.slug == "teacher").first()
        u = User(role_id=role.id, name=data.name, username=data.username,
                 password_hash=hash_password(data.password), status="active", must_change_password=True)
        db.add(u); db.flush()
        user_id = u.id
    t = Teacher(employee_code=teacher_code(db), user_id=user_id, name=data.name, contact=data.contact,
                whatsapp_number=data.whatsapp_number, email=data.email, cnic=data.cnic,
                qualification=data.qualification, address=data.address, joining_date=data.joining_date,
                basic_salary=data.basic_salary, status=data.status)
    db.add(t); db.commit(); db.refresh(t)
    return teacher_out(t)


@router.post("/{teacher_id}")
def update_teacher(teacher_id: int, data: TeacherIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.manage")(user, db)
    t = db.get(Teacher, teacher_id)
    if not t:
        raise HTTPException(404)
    for field in ["name","contact","whatsapp_number","email","cnic","qualification","address","joining_date","basic_salary","status"]:
        setattr(t, field, getattr(data, field))
    db.commit(); db.refresh(t)
    return teacher_out(t)


@router.post("/{teacher_id}/status")
def toggle_teacher(teacher_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.manage")(user, db)
    t = db.get(Teacher, teacher_id)
    if not t:
        raise HTTPException(404)
    t.status = "inactive" if t.status == "active" else "active"
    db.commit()
    return {"status": t.status}


@router.post("/{teacher_id}/assignments")
def add_assignment(teacher_id: int, class_id: int, subject_id: Optional[int] = None,
                   session_id: Optional[int] = None, is_class_teacher: bool = False,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.manage")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    a = TeacherAssignment(teacher_id=teacher_id, class_id=class_id, subject_id=subject_id,
                          academic_session_id=session_id, is_class_teacher=is_class_teacher)
    db.add(a); db.commit(); db.refresh(a)
    return {"id": a.id}


@router.post("/{teacher_id}/assignments/{assignment_id}/delete")
def remove_assignment(teacher_id: int, assignment_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.manage")(user, db)
    a = db.get(TeacherAssignment, assignment_id)
    if not a or a.teacher_id != teacher_id:
        raise HTTPException(404)
    db.delete(a); db.commit()
    return {"ok": True}


@router.get("/{teacher_id}/attendance")
def teacher_attendance_list(teacher_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("teachers.view")(user, db)
    from app.models import TeacherAttendance
    rows = db.query(TeacherAttendance).filter(TeacherAttendance.teacher_id == teacher_id).order_by(TeacherAttendance.date.desc()).limit(100).all()
    return [{"id": r.id, "date": str(r.date), "status": r.status, "remarks": r.remarks} for r in rows]
