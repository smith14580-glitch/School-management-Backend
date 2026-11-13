from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import StudentEnrollment, Student, SchoolClass, AcademicSession

router = APIRouter(prefix="/api/class-students", tags=["class-students"])


class TransferIn(BaseModel):
    to_class_id: int
    to_session_id: Optional[int] = None
    roll_number: Optional[int] = None


@router.post("/{enrollment_id}/remove")
def remove(enrollment_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.manage")(user, db)
    e = db.get(StudentEnrollment, enrollment_id)
    if not e:
        raise HTTPException(404)
    e.status = "left"
    e.ended_on = date.today()
    st = db.get(Student, e.student_id)
    if st:
        st.status = "inactive"
    db.commit()
    return {"ok": True}


@router.post("/{enrollment_id}/transfer")
def transfer(enrollment_id: int, data: TransferIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("students.manage")(user, db)
    e = db.get(StudentEnrollment, enrollment_id)
    if not e:
        raise HTTPException(404)
    sess_id = data.to_session_id
    if not sess_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        sess_id = cs.id if cs else e.academic_session_id
    # close old
    e.status = "transferred"
    e.ended_on = date.today()
    # roll number
    roll = data.roll_number
    if roll is None:
        existing = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == data.to_class_id, StudentEnrollment.academic_session_id == sess_id).all()
        used = {x.roll_number for x in existing}
        roll = 1
        while roll in used:
            roll += 1
    new_e = StudentEnrollment(student_id=e.student_id, class_id=data.to_class_id, academic_session_id=sess_id,
                              roll_number=roll, status="active", enrolled_on=date.today())
    db.add(new_e)
    from app.models import PromotionLog
    db.add(PromotionLog(student_id=e.student_id, from_class_id=e.class_id, to_class_id=data.to_class_id,
                        from_session_id=e.academic_session_id, to_session_id=sess_id, action="transferred",
                        performed_by=user.id))
    db.commit(); db.refresh(new_e)
    return {"enrollment_id": new_e.id, "roll_number": new_e.roll_number}
