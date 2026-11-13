from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.core.security import hash_password
from app.models import User, Role

router = APIRouter(prefix="/api/users", tags=["users"])


class UserIn(BaseModel):
    name: str
    username: str
    email: Optional[str] = None
    role_id: int
    password: Optional[str] = None
    status: str = "active"


@router.get("")
def list_users(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("users.manage")(user, db)
    rows = db.query(User).order_by(User.name).all()
    return [{"id": u.id, "name": u.name, "username": u.username, "email": u.email,
             "role_id": u.role_id, "role_name": (db.get(Role, u.role_id).name if db.get(Role, u.role_id) else ""),
             "status": u.status} for u in rows]


@router.get("/roles")
def roles(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return [{"id": r.id, "name": r.name, "slug": r.slug} for r in db.query(Role).all()]


@router.post("")
def create_user(data: UserIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("users.manage")(user, db)
    u = User(name=data.name, username=data.username, email=data.email, role_id=data.role_id,
             password_hash=hash_password(data.password or "ChangeMe@123"), status=data.status, must_change_password=True)
    db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id}


@router.post("/{uid}")
def update_user(uid: int, data: UserIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("users.manage")(user, db)
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404)
    u.name = data.name; u.username = data.username; u.email = data.email; u.role_id = data.role_id; u.status = data.status
    db.commit()
    return {"ok": True}


@router.post("/{uid}/status")
def toggle_user(uid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("users.manage")(user, db)
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404)
    u.status = "inactive" if u.status == "active" else "active"
    db.commit()
    return {"status": u.status}


@router.post("/{uid}/password")
def reset_password(uid: int, password: str, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("users.manage")(user, db)
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404)
    u.password_hash = hash_password(password)
    u.must_change_password = True
    db.commit()
    return {"ok": True}
