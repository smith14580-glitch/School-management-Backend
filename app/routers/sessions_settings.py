from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import AcademicSession, Setting

router = APIRouter(prefix="/api/sessions", tags=["sessions"])
settings_router = APIRouter(prefix="/api/settings", tags=["settings"])


class SessionIn(BaseModel):
    year_label: str
    start_date: date
    end_date: date
    is_current: bool = False
    is_locked: bool = False


@router.get("")
def list_sessions(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("sessions.view")(user, db)
    rows = db.query(AcademicSession).order_by(AcademicSession.start_date.desc()).all()
    return [{"id": s.id, "year_label": s.year_label, "start_date": str(s.start_date), "end_date": str(s.end_date),
             "is_current": s.is_current, "is_locked": s.is_locked} for s in rows]


@router.post("")
def create_session(data: SessionIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("sessions.manage")(user, db)
    if data.is_current:
        db.query(AcademicSession).update({AcademicSession.is_current: False})
    s = AcademicSession(**data.model_dump())
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id}


@router.post("/{sid}")
def update_session(sid: int, data: SessionIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("sessions.manage")(user, db)
    s = db.get(AcademicSession, sid)
    if not s:
        raise HTTPException(404)
    if data.is_current:
        db.query(AcademicSession).filter(AcademicSession.id != sid).update({AcademicSession.is_current: False})
    for k, v in data.model_dump().items():
        setattr(s, k, v)
    db.commit()
    return {"ok": True}


@router.post("/{sid}/current")
def make_current(sid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("sessions.manage")(user, db)
    db.query(AcademicSession).update({AcademicSession.is_current: False})
    s = db.get(AcademicSession, sid)
    s.is_current = True
    db.commit()
    return {"ok": True}


@router.post("/{sid}/lock")
def toggle_lock(sid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("sessions.manage")(user, db)
    s = db.get(AcademicSession, sid)
    if not s:
        raise HTTPException(404)
    s.is_locked = not s.is_locked
    db.commit()
    return {"is_locked": s.is_locked}


# settings
@settings_router.get("")
def get_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("settings.view")(user, db)
    rows = db.query(Setting).all()
    return {r.setting_key: r.setting_value for r in rows}


@settings_router.post("")
def save_settings(data: dict, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("settings.view")(user, db)  # view only per perms; manage not granted except admin wildcard
    for k, v in data.items():
        r = db.query(Setting).filter(Setting.setting_key == k).first()
        if r:
            r.setting_value = v
        else:
            db.add(Setting(setting_key=k, setting_value=v))
    db.commit()
    return {"ok": True}
