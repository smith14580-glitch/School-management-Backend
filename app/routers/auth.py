from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.core.deps import get_current_user
from app.models import User, Role

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if user.status != "active":
        raise HTTPException(status_code=403, detail="Inactive account")
    role = db.get(Role, user.role_id)
    token = create_access_token({"sub": str(user.id), "role": role.slug})
    user.last_login_at = __import__("datetime").datetime.utcnow()
    db.commit()
    return TokenOut(access_token=token, user={
        "id": user.id, "name": user.name, "username": user.username,
        "role": role.slug, "role_name": role.name, "must_change_password": user.must_change_password,
    })


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.get(Role, user.role_id)
    return {"id": user.id, "name": user.name, "username": user.username,
            "role": role.slug, "role_name": role.name, "must_change_password": user.must_change_password}
