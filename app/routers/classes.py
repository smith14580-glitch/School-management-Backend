from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.scoping import scoped_classes_query, teacher_class_ids
from app.models import SchoolClass, Subject, AcademicSession, StudentEnrollment, Student

router = APIRouter(prefix="/api/classes", tags=["classes"])


class ClassIn(BaseModel):
    academic_session_id: int
    name: str
    section: Optional[str] = None
    class_order: int = 0
    is_final_year: bool = False
    capacity: Optional[int] = None
    is_active: bool = True


class SubjectIn(BaseModel):
    name: str
    code: Optional[str] = None


def cls_out(c):
    return {
        "id": c.id, "academic_session_id": c.academic_session_id, "name": c.name,
        "section": c.section, "class_order": c.class_order, "is_final_year": c.is_final_year,
        "capacity": c.capacity, "is_active": c.is_active,
    }


@router.get("")
def list_classes(session_id: Optional[int] = None, q: Optional[str] = None,
                user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("classes.view")(user, db)
    query = scoped_classes_query(user, db)
    if session_id:
        query = query.filter(SchoolClass.academic_session_id == session_id)
    if q:
        query = query.filter(SchoolClass.name.ilike(f"%{q}%"))
    items = query.order_by(SchoolClass.class_order, SchoolClass.name).all()
    # attach subject count + student count
    out = []
    for c in items:
        sc = db.query(Subject).filter(Subject.class_id == c.id, Subject.is_active == True).count()
        ec = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == c.id, StudentEnrollment.status == "active").count()
        d = cls_out(c)
        d["subject_count"] = sc
        d["student_count"] = ec
        out.append(d)
    return out


@router.get("/{class_id}")
def get_class(class_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("classes.view")(user, db)
    c = db.get(SchoolClass, class_id)
    if not c:
        raise HTTPException(404, "Not found")
    ids = teacher_class_ids(user, db)
    if ids is not None and class_id not in ids:
        raise HTTPException(403, "Forbidden")
    subjects = db.query(Subject).filter(Subject.class_id == class_id).order_by(Subject.name).all()
    return {
        "class": cls_out(c),
        "subjects": [{"id": s.id, "name": s.name, "code": s.code, "is_active": s.is_active} for s in subjects],
    }


@router.post("")
def create_class(data: ClassIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("classes.manage")(user, db)
    c = SchoolClass(**data.model_dump())
    db.add(c); db.commit(); db.refresh(c)
    return cls_out(c)


@router.post("/{class_id}")
def update_class(class_id: int, data: ClassIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("classes.manage")(user, db)
    c = db.get(SchoolClass, class_id)
    if not c:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(c, k, v)
    db.commit(); db.refresh(c)
    return cls_out(c)


@router.post("/{class_id}/status")
def toggle_class(class_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("classes.manage")(user, db)
    c = db.get(SchoolClass, class_id)
    if not c:
        raise HTTPException(404)
    c.is_active = not c.is_active
    db.commit()
    return {"is_active": c.is_active}


@router.post("/{class_id}/subjects")
def add_subject(class_id: int, data: SubjectIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("subjects.manage")(user, db)
    s = Subject(class_id=class_id, name=data.name, code=data.code)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "name": s.name, "code": s.code, "is_active": s.is_active}


@router.post("/{class_id}/subjects/{subject_id}/status")
def toggle_subject(class_id: int, subject_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("subjects.manage")(user, db)
    s = db.get(Subject, subject_id)
    if not s or s.class_id != class_id:
        raise HTTPException(404)
    s.is_active = not s.is_active
    db.commit()
    return {"is_active": s.is_active}


@router.post("/{class_id}/subjects/{subject_id}/delete")
def delete_subject(class_id: int, subject_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("subjects.manage")(user, db)
    s = db.get(Subject, subject_id)
    if not s or s.class_id != class_id:
        raise HTTPException(404)
    db.delete(s); db.commit()
    return {"ok": True}


@router.get("/{class_id}/students")
def class_students(class_id: int, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.view")(user, db)
    if session_id is None:
        # current session
        sess = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = sess.id if sess else None
    q = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == class_id)
    if session_id:
        q = q.filter(StudentEnrollment.academic_session_id == session_id)
    enrollments = q.order_by(StudentEnrollment.roll_number).all()
    out = []
    for e in enrollments:
        st = db.get(Student, e.student_id)
        out.append({
            "enrollment_id": e.id, "student_id": st.id, "student_code": st.student_code,
            "name": st.name, "father_guardian_name": st.father_guardian_name,
            "roll_number": e.roll_number, "status": e.status, "enrolled_on": str(e.enrolled_on),
        })
    return out


@router.get("/{class_id}/export")
def export_roster(class_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("classes.view")(user, db)
    data = class_students(class_id, None, user, db)
    return {"rows": data}
