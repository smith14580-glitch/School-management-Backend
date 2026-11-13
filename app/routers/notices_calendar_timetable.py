from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date, datetime

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import Notice, CalendarEvent, TimetableSlot, AcademicSession

notices_router = APIRouter(prefix="/api/notices", tags=["notices"])
calendar_router = APIRouter(prefix="/api/calendar", tags=["calendar"])
timetable_router = APIRouter(prefix="/api/timetable", tags=["timetable"])


class NoticeIn(BaseModel):
    title: str
    body: str
    audience: str = "all"
    role_id: Optional[int] = None
    class_id: Optional[int] = None
    is_active: bool = True


@notices_router.get("")
def list_notices(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("notices.view")(user, db)
    rows = db.query(Notice).order_by(Notice.publish_at.desc()).all()
    return [{"id": n.id, "title": n.title, "body": n.body, "audience": n.audience,
             "role_id": n.role_id, "class_id": n.class_id, "is_active": n.is_active,
             "publish_at": str(n.publish_at)} for n in rows]


@notices_router.post("")
def create_notice(data: NoticeIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("notices.manage")(user, db)
    n = Notice(**data.model_dump(), published_by=user.id)
    db.add(n); db.commit(); db.refresh(n)
    return {"id": n.id}


@notices_router.post("/{nid}")
def update_notice(nid: int, data: NoticeIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("notices.manage")(user, db)
    n = db.get(Notice, nid)
    if not n:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(n, k, v)
    db.commit()
    return {"ok": True}


@notices_router.post("/{nid}/status")
def toggle_notice(nid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("notices.manage")(user, db)
    n = db.get(Notice, nid)
    if not n:
        raise HTTPException(404)
    n.is_active = not n.is_active
    db.commit()
    return {"is_active": n.is_active}


@notices_router.post("/{nid}/delete")
def delete_notice(nid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("notices.manage")(user, db)
    n = db.get(Notice, nid)
    if not n:
        raise HTTPException(404)
    db.delete(n); db.commit()
    return {"ok": True}


# calendar
class CalIn(BaseModel):
    academic_session_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    event_type: str = "event"
    start_date: date
    end_date: date
    class_id: Optional[int] = None


@calendar_router.get("")
def list_events(session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("calendar.view")(user, db)
    q = db.query(CalendarEvent)
    if session_id:
        q = q.filter(CalendarEvent.academic_session_id == session_id)
    rows = q.order_by(CalendarEvent.start_date).all()
    return [{"id": e.id, "title": e.title, "description": e.description, "event_type": e.event_type,
             "start_date": str(e.start_date), "end_date": str(e.end_date), "class_id": e.class_id} for e in rows]


@calendar_router.post("")
def create_event(data: CalIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("calendar.manage")(user, db)
    sess_id = data.academic_session_id
    if not sess_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        sess_id = cs.id if cs else 1
    d = data.model_dump(); d["academic_session_id"] = sess_id
    e = CalendarEvent(**d, created_by=user.id)
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id}


@calendar_router.post("/{eid}")
def update_event(eid: int, data: CalIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("calendar.manage")(user, db)
    e = db.get(CalendarEvent, eid)
    if not e:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        if v is not None:
            setattr(e, k, v)
    db.commit()
    return {"ok": True}


@calendar_router.post("/{eid}/delete")
def delete_event(eid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("calendar.manage")(user, db)
    e = db.get(CalendarEvent, eid)
    if not e:
        raise HTTPException(404)
    db.delete(e); db.commit()
    return {"ok": True}


# timetable
class SlotIn(BaseModel):
    class_id: int
    academic_session_id: Optional[int] = None
    day_of_week: int
    start_time: str
    end_time: str
    subject_id: Optional[int] = None
    teacher_id: Optional[int] = None
    room: Optional[str] = None


@timetable_router.get("")
def list_slots(class_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("timetable.view")(user, db)
    q = db.query(TimetableSlot)
    if class_id:
        q = q.filter(TimetableSlot.class_id == class_id)
    rows = q.order_by(TimetableSlot.day_of_week, TimetableSlot.start_time).all()
    return [{"id": s.id, "class_id": s.class_id, "day_of_week": s.day_of_week,
             "start_time": s.start_time, "end_time": s.end_time, "subject_id": s.subject_id,
             "teacher_id": s.teacher_id, "room": s.room} for s in rows]


@timetable_router.post("")
def create_slot(data: SlotIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("timetable.manage")(user, db)
    sess_id = data.academic_session_id
    if not sess_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        sess_id = cs.id if cs else 1
    d = data.model_dump(); d["academic_session_id"] = sess_id
    s = TimetableSlot(**d)
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id}


@timetable_router.post("/{sid}/delete")
def delete_slot(sid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("timetable.manage")(user, db)
    s = db.get(TimetableSlot, sid)
    if not s:
        raise HTTPException(404)
    db.delete(s); db.commit()
    return {"ok": True}
