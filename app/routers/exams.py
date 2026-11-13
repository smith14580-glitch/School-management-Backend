from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import Exam, ExamSubject, ExamResult, ExamResultSummary, SchoolClass, Subject, AcademicSession, Student, StudentEnrollment

router = APIRouter(prefix="/api/exams", tags=["exams"])
results_router = APIRouter(prefix="/api/exam-results", tags=["exam-results"])


class ExamIn(BaseModel):
    academic_session_id: Optional[int] = None
    class_id: int
    name: str
    term: Optional[str] = None
    start_date: date
    end_date: date
    status: str = "draft"


class ExamSubjectIn(BaseModel):
    subject_id: int
    total_marks: float = 100
    passing_marks: float = 33
    exam_date: Optional[date] = None
    exam_time: Optional[str] = None
    teacher_id: Optional[int] = None


@router.get("")
def list_exams(class_id: Optional[int] = None, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("exams.view")(user, db)
    q = db.query(Exam)
    if class_id:
        q = q.filter(Exam.class_id == class_id)
    if session_id:
        q = q.filter(Exam.academic_session_id == session_id)
    rows = q.order_by(Exam.start_date.desc()).all()
    return [{"id": e.id, "academic_session_id": e.academic_session_id, "class_id": e.class_id, "name": e.name,
             "term": e.term, "start_date": str(e.start_date), "end_date": str(e.end_date), "status": e.status} for e in rows]


@router.get("/{exam_id}")
def get_exam(exam_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("exams.view")(user, db)
    e = db.get(Exam, exam_id)
    if not e:
        raise HTTPException(404)
    subs = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id).all()
    return {"exam": {"id": e.id, "class_id": e.class_id, "name": e.name, "term": e.term,
                     "start_date": str(e.start_date), "end_date": str(e.end_date), "status": e.status},
            "subjects": [{"id": s.id, "subject_id": s.subject_id, "subject_name": (db.get(Subject, s.subject_id).name if db.get(Subject, s.subject_id) else ""),
                          "total_marks": float(s.total_marks), "passing_marks": float(s.passing_marks),
                          "exam_date": str(s.exam_date) if s.exam_date else None, "exam_time": s.exam_time, "teacher_id": s.teacher_id} for s in subs]}


@router.post("")
def create_exam(data: ExamIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("exams.manage")(user, db)
    sess_id = data.academic_session_id
    if not sess_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        sess_id = cs.id if cs else 1
    e = Exam(academic_session_id=sess_id, class_id=data.class_id, name=data.name, term=data.term,
             start_date=data.start_date, end_date=data.end_date, status=data.status, created_by=user.id)
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id}


@router.post("/{exam_id}/subjects")
def add_exam_subject(exam_id: int, data: ExamSubjectIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("exams.manage")(user, db)
    es = ExamSubject(exam_id=exam_id, subject_id=data.subject_id, total_marks=data.total_marks,
                     passing_marks=data.passing_marks, exam_date=data.exam_date, exam_time=data.exam_time,
                     teacher_id=data.teacher_id)
    db.add(es); db.commit(); db.refresh(es)
    return {"id": es.id}


@router.post("/{exam_id}/subjects/{subject_id}/delete")
def remove_exam_subject(exam_id: int, subject_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("exams.manage")(user, db)
    es = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id, ExamSubject.subject_id == subject_id).first()
    if not es:
        raise HTTPException(404)
    db.delete(es); db.commit()
    return {"ok": True}


@router.post("/{exam_id}/status")
def advance_status(exam_id: int, status: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("exams.manage")(user, db)
    e = db.get(Exam, exam_id)
    if not e:
        raise HTTPException(404)
    e.status = status
    db.commit()
    return {"status": e.status}


# ---- results ----
@results_router.get("")
def results_index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("results.view")(user, db)
    return [{"id": e.id, "name": e.name, "class_id": e.class_id, "status": e.status} for e in db.query(Exam).all()]


@results_router.get("/exam/{exam_id}/roster")
def exam_roster(exam_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("results.view")(user, db)
    e = db.get(Exam, exam_id)
    if not e:
        raise HTTPException(404)
    enrs = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == e.class_id, StudentEnrollment.academic_session_id == e.academic_session_id, StudentEnrollment.status == "active").all()
    out = []
    for enr in enrs:
        st = db.get(Student, enr.student_id)
        summary = db.query(ExamResultSummary).filter(ExamResultSummary.exam_id == exam_id, ExamResultSummary.student_id == st.id).first()
        out.append({"student_id": st.id, "name": st.name, "roll_number": enr.roll_number,
                    "finalized": bool(summary.is_locked) if summary else False,
                    "percentage": float(summary.percentage) if summary else None})
    return out


@results_router.get("/exam/{exam_id}/student/{student_id}")
def get_result(exam_id: int, student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("results.view")(user, db)
    e = db.get(Exam, exam_id)
    subs = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id).all()
    marks = db.query(ExamResult).filter(ExamResult.exam_id == exam_id, ExamResult.student_id == student_id).all()
    mmap = {(m.subject_id): m for m in marks}
    summary = db.query(ExamResultSummary).filter(ExamResultSummary.exam_id == exam_id, ExamResultSummary.student_id == student_id).first()
    return {
        "exam": {"id": e.id, "name": e.name, "class_id": e.class_id},
        "subjects": [{"subject_id": s.subject_id, "subject_name": (db.get(Subject, s.subject_id).name if db.get(Subject, s.subject_id) else ""),
                      "total_marks": float(s.total_marks), "passing_marks": float(s.passing_marks),
                      "marks_obtained": (float(mmap[s.subject_id].marks_obtained) if s.subject_id in mmap and mmap[s.subject_id].marks_obtained is not None else None),
                      "is_absent": mmap[s.subject_id].is_absent if s.subject_id in mmap else False} for s in subs],
        "summary": {
            "total_obtained": float(summary.total_obtained) if summary else 0,
            "total_possible": float(summary.total_possible) if summary else 0,
            "percentage": float(summary.percentage) if summary else 0,
            "grade": summary.grade if summary else None,
            "position": summary.position if summary else None,
            "result_status": summary.result_status if summary else "pending",
            "attendance_present": summary.attendance_present if summary else 0,
            "attendance_total": summary.attendance_total if summary else 0,
            "attendance_percent": float(summary.attendance_percent) if summary else 0,
            "remarks": summary.remarks if summary else None,
            "is_locked": summary.is_locked if summary else False,
        } if summary else None,
    }


@results_router.post("/exam/{exam_id}/student/{student_id}")
def save_result(exam_id: int, student_id: int, data: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    # permission: results.manage or results.enter
    from app.core.permissions import has_permission
    from app.core.deps import current_role_slug
    slug = current_role_slug(user, db)
    if not (has_permission(slug, "results.manage") or has_permission(slug, "results.enter")):
        raise HTTPException(403, "Forbidden")
    e = db.get(Exam, exam_id)
    subs = db.query(ExamSubject).filter(ExamSubject.exam_id == exam_id).all()
    total_obt = 0.0
    total_pos = 0.0
    for s in subs:
        sid = s.subject_id
        entry = (data.get("marks") or {}).get(str(sid)) if isinstance(data.get("marks"), dict) else None
        # support list form
        mo = None
        is_absent = False
        remarks = None
        if isinstance(data.get("marks"), list):
            for m in data["marks"]:
                if m.get("subject_id") == sid:
                    mo = m.get("marks_obtained")
                    is_absent = m.get("is_absent", False)
                    remarks = m.get("remarks")
        elif isinstance(data.get("marks"), dict):
            v = data["marks"].get(str(sid)) or data["marks"].get(sid)
            if isinstance(v, dict):
                mo = v.get("marks_obtained"); is_absent = v.get("is_absent", False); remarks = v.get("remarks")
            else:
                mo = v
        existing = db.query(ExamResult).filter(ExamResult.exam_id == exam_id, ExamResult.student_id == student_id, ExamResult.subject_id == sid).first()
        if existing:
            existing.marks_obtained = mo
            existing.is_absent = is_absent
            existing.remarks = remarks
            existing.entered_by = user.id
        else:
            db.add(ExamResult(exam_id=exam_id, student_id=student_id, subject_id=sid, marks_obtained=mo, is_absent=is_absent, remarks=remarks, entered_by=user.id))
        if mo is not None:
            total_obt += float(mo)
        total_pos += float(s.total_marks)
    db.flush()
    # attendance snapshot
    att_rows = db.query(__import__("app.models", fromlist=["Attendance"]).Attendance).filter(
        __import__("app.models", fromlist=["Attendance"]).Attendance.student_id == student_id,
        __import__("app.models", fromlist=["Attendance"]).Attendance.date >= e.start_date,
        __import__("app.models", fromlist=["Attendance"]).Attendance.date <= e.end_date).all()
    present = sum(1 for a in att_rows if a.status in ("present", "late"))
    total_att = len(att_rows)
    att_pct = (present / total_att * 100) if total_att else 0.0
    pct = (total_obt / total_pos * 100) if total_pos else 0.0
    grade = None
    if pct >= 80: grade = "A+"
    elif pct >= 70: grade = "A"
    elif pct >= 60: grade = "B"
    elif pct >= 50: grade = "C"
    elif pct >= 40: grade = "D"
    else: grade = "F"
    status_res = "pass" if pct >= 40 else "fail"
    summary = db.query(ExamResultSummary).filter(ExamResultSummary.exam_id == exam_id, ExamResultSummary.student_id == student_id).first()
    if summary:
        summary.total_obtained = total_obt
        summary.total_possible = total_pos
        summary.percentage = pct
        summary.grade = grade
        summary.result_status = status_res
        summary.attendance_present = present
        summary.attendance_total = total_att
        summary.attendance_percent = att_pct
        summary.remarks = data.get("remarks")
    else:
        db.add(ExamResultSummary(exam_id=exam_id, student_id=student_id, total_obtained=total_obt,
                                 total_possible=total_pos, percentage=pct, grade=grade, result_status=status_res,
                                 attendance_present=present, attendance_total=total_att, attendance_percent=att_pct,
                                 remarks=data.get("remarks")))
    db.commit()
    return {"ok": True, "percentage": pct, "grade": grade}


@results_router.post("/exam/{exam_id}/student/{student_id}/finalize")
def finalize(exam_id: int, student_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("results.manage")(user, db)
    summary = db.query(ExamResultSummary).filter(ExamResultSummary.exam_id == exam_id, ExamResultSummary.student_id == student_id).first()
    if not summary:
        raise HTTPException(400, "Save result first")
    summary.is_locked = True
    summary.finalized_by = user.id
    from datetime import datetime
    summary.finalized_at = datetime.utcnow()
    db.commit()
    return {"ok": True}
