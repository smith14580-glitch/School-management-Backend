from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.scoping import teacher_class_ids
from app.models import Attendance, Student, SchoolClass, AcademicSession, StudentEnrollment

router = APIRouter(prefix="/api/attendance", tags=["attendance"])


class AttendanceIn(BaseModel):
    student_id: int
    class_id: int
    date: date
    status: str
    remarks: Optional[str] = None


@router.get("")
def index(class_id: Optional[int] = None, date_str: Optional[str] = None, session_id: Optional[int] = None,
          user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("attendance.view")(user, db)
    d = date.fromisoformat(date_str) if date_str else date.today()
    q = db.query(Attendance).filter(Attendance.date == d)
    if class_id:
        q = q.filter(Attendance.class_id == class_id)
    rows = q.all()
    return [{"id": r.id, "student_id": r.student_id, "class_id": r.class_id, "date": str(r.date),
             "status": r.status, "remarks": r.remarks} for r in rows]


@router.post("")
def store(items: List[AttendanceIn], user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("attendance.manage")(user, db)
    for it in items:
        existing = db.query(Attendance).filter(Attendance.student_id == it.student_id, Attendance.date == it.date).first()
        if existing:
            existing.status = it.status
            existing.remarks = it.remarks
            existing.class_id = it.class_id
            existing.marked_by = user.id
        else:
            db.add(Attendance(student_id=it.student_id, class_id=it.class_id, date=it.date,
                              status=it.status, remarks=it.remarks, marked_by=user.id))
    db.commit()
    return {"ok": True}


@router.get("/report")
def report(class_id: Optional[int] = None, from_date: Optional[str] = None, to_date: Optional[str] = None,
           user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("attendance.view")(user, db)
    q = db.query(Attendance)
    if class_id:
        q = q.filter(Attendance.class_id == class_id)
    if from_date:
        q = q.filter(Attendance.date >= date.fromisoformat(from_date))
    if to_date:
        q = q.filter(Attendance.date <= date.fromisoformat(to_date))
    rows = q.all()
    # aggregate per student
    agg = {}
    for r in rows:
        a = agg.setdefault(r.student_id, {"present": 0, "absent": 0, "leave": 0, "late": 0, "total": 0})
        a[r.status] = a.get(r.status, 0) + 1
        a["total"] += 1
    out = []
    for sid, a in agg.items():
        st = db.get(Student, sid)
        out.append({"student_id": sid, "name": st.name if st else "", "counts": a})
    return out


@router.get("/students/{student_id}")
def student_attendance(student_id: int, from_date: Optional[str] = None, to_date: Optional[str] = None,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("attendance.view")(user, db)
    q = db.query(Attendance).filter(Attendance.student_id == student_id)
    if from_date:
        q = q.filter(Attendance.date >= date.fromisoformat(from_date))
    if to_date:
        q = q.filter(Attendance.date <= date.fromisoformat(to_date))
    rows = q.order_by(Attendance.date.desc()).all()
    return [{"id": r.id, "date": str(r.date), "status": r.status, "remarks": r.remarks} for r in rows]
