from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import DailyTest, DailyTestMark, Student, SchoolClass, Subject

router = APIRouter(prefix="/api/tests", tags=["tests"])


class TestIn(BaseModel):
    class_id: int
    subject_id: int
    title: str
    test_date: date
    total_marks: float


class MarksIn(BaseModel):
    marks: List[dict]  # {student_id, marks_obtained, remarks}


@router.get("")
def list_tests(class_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("tests.view")(user, db)
    q = db.query(DailyTest)
    if class_id:
        q = q.filter(DailyTest.class_id == class_id)
    rows = q.order_by(DailyTest.test_date.desc()).all()
    return [{"id": t.id, "class_id": t.class_id, "subject_id": t.subject_id, "title": t.title,
             "test_date": str(t.test_date), "total_marks": float(t.total_marks)} for t in rows]


@router.get("/{test_id}")
def get_test(test_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("tests.view")(user, db)
    t = db.get(DailyTest, test_id)
    if not t:
        raise HTTPException(404)
    marks = db.query(DailyTestMark).filter(DailyTestMark.daily_test_id == test_id).all()
    return {"test": {"id": t.id, "class_id": t.class_id, "subject_id": t.subject_id, "title": t.title,
                     "test_date": str(t.test_date), "total_marks": float(t.total_marks)},
            "marks": [{"student_id": m.student_id, "marks_obtained": (float(m.marks_obtained) if m.marks_obtained is not None else None), "remarks": m.remarks} for m in marks]}


@router.post("")
def create_test(data: TestIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("tests.manage")(user, db)
    t = DailyTest(class_id=data.class_id, subject_id=data.subject_id, title=data.title,
                  test_date=data.test_date, total_marks=data.total_marks, created_by=user.id)
    db.add(t); db.commit(); db.refresh(t)
    return {"id": t.id}


@router.post("/{test_id}/marks")
def save_marks(test_id: int, data: MarksIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("tests.manage")(user, db)
    for m in data.marks:
        existing = db.query(DailyTestMark).filter(DailyTestMark.daily_test_id == test_id, DailyTestMark.student_id == m["student_id"]).first()
        val = m.get("marks_obtained")
        if existing:
            existing.marks_obtained = val
            existing.remarks = m.get("remarks")
        else:
            db.add(DailyTestMark(daily_test_id=test_id, student_id=m["student_id"], marks_obtained=val, remarks=m.get("remarks")))
    db.commit()
    return {"ok": True}


@router.post("/{test_id}/delete")
def delete_test(test_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("tests.manage")(user, db)
    t = db.get(DailyTest, test_id)
    if not t:
        raise HTTPException(404)
    db.delete(t); db.commit()
    return {"ok": True}
