from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import TeacherSalary, Teacher, TeacherSalaryHistory

router = APIRouter(prefix="/api/salaries", tags=["salaries"])


class SalaryGenIn(BaseModel):
    month: int
    year: int
    basic_salary: float
    allowances: float = 0
    deductions: float = 0


@router.get("")
def index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.view")(user, db)
    teachers = db.query(Teacher).filter(Teacher.status == "active").all()
    return [{"id": t.id, "name": t.name, "employee_code": t.employee_code} for t in teachers]


@router.get("/teachers/{teacher_id}")
def show(teacher_id: int, year: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.view")(user, db)
    q = db.query(TeacherSalary).filter(TeacherSalary.teacher_id == teacher_id)
    if year:
        q = q.filter(TeacherSalary.year == year)
    rows = q.order_by(TeacherSalary.year, TeacherSalary.month).all()
    return [{"id": r.id, "month": r.month, "year": r.year, "basic_salary": float(r.basic_salary or 0),
             "allowances": float(r.allowances or 0), "deductions": float(r.deductions or 0),
             "net_amount": float(r.net_amount or 0), "status": r.status, "paid_amount": float(r.paid_amount or 0),
             "paid_date": str(r.paid_date) if r.paid_date else None, "notes": r.notes} for r in rows]


@router.post("/teachers/{teacher_id}/generate")
def generate(teacher_id: int, data: SalaryGenIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.manage")(user, db)
    net = data.basic_salary + data.allowances - data.deductions
    existing = db.query(TeacherSalary).filter(TeacherSalary.teacher_id == teacher_id, TeacherSalary.month == data.month, TeacherSalary.year == data.year).first()
    if existing:
        existing.basic_salary = data.basic_salary
        existing.allowances = data.allowances
        existing.deductions = data.deductions
        existing.net_amount = net
        db.commit(); db.refresh(existing)
        return {"id": existing.id}
    r = TeacherSalary(teacher_id=teacher_id, month=data.month, year=data.year, basic_salary=data.basic_salary,
                      allowances=data.allowances, deductions=data.deductions, net_amount=net, recorded_by=user.id)
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}


@router.post("/records/{record_id}")
def update_record(record_id: int, basic_salary: Optional[float] = None, allowances: Optional[float] = None,
                  deductions: Optional[float] = None, notes: Optional[str] = None,
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.manage")(user, db)
    r = db.get(TeacherSalary, record_id)
    if not r:
        raise HTTPException(404)
    if basic_salary is not None: r.basic_salary = basic_salary
    if allowances is not None: r.allowances = allowances
    if deductions is not None: r.deductions = deductions
    r.net_amount = (r.basic_salary or 0) + (r.allowances or 0) - (r.deductions or 0)
    r.notes = notes
    db.commit()
    return {"ok": True}


@router.post("/records/{record_id}/pay")
def pay(record_id: int, amount: float, paid_date: Optional[date] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.manage")(user, db)
    r = db.get(TeacherSalary, record_id)
    if not r:
        raise HTTPException(404)
    r.paid_amount = (r.paid_amount or 0) + amount
    r.paid_date = paid_date or date.today()
    if r.paid_amount >= r.net_amount:
        r.status = "paid"
    elif r.paid_amount > 0:
        r.status = "partial"
    db.commit()
    return {"status": r.status, "paid_amount": float(r.paid_amount)}


@router.get("/teachers/{teacher_id}/increase")
def increase_form(teacher_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.manage")(user, db)
    t = db.get(Teacher, teacher_id)
    return {"basic_salary": float(t.basic_salary or 0)}


@router.post("/teachers/{teacher_id}/increase")
def apply_increase(teacher_id: int, new_salary: float, effective_date: date, reason: Optional[str] = None,
                   user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.manage")(user, db)
    t = db.get(Teacher, teacher_id)
    if not t:
        raise HTTPException(404)
    prev = float(t.basic_salary or 0)
    db.add(TeacherSalaryHistory(teacher_id=teacher_id, previous_salary=prev, new_salary=new_salary,
                                increase_amount=new_salary - prev, effective_date=effective_date, reason=reason, changed_by=user.id))
    t.basic_salary = new_salary
    db.commit()
    return {"ok": True}


@router.get("/teachers/{teacher_id}/history")
def history(teacher_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.view")(user, db)
    rows = db.query(TeacherSalaryHistory).filter(TeacherSalaryHistory.teacher_id == teacher_id).order_by(TeacherSalaryHistory.effective_date.desc()).all()
    return [{"id": r.id, "previous_salary": float(r.previous_salary), "new_salary": float(r.new_salary),
             "increase_amount": float(r.increase_amount), "effective_date": str(r.effective_date), "reason": r.reason} for r in rows]


@router.get("/records/{record_id}/voucher")
def voucher(record_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("salaries.view")(user, db)
    r = db.get(TeacherSalary, record_id)
    if not r:
        raise HTTPException(404)
    t = db.get(Teacher, r.teacher_id)
    return {"record": {"id": r.id, "month": r.month, "year": r.year, "net_amount": float(r.net_amount or 0),
                       "paid_amount": float(r.paid_amount or 0), "status": r.status},
            "teacher": {"id": t.id, "name": t.name, "employee_code": t.employee_code} if t else None}
