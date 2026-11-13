from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import date

from app.core.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models import FeeType, ClassFeeType, FeeRecord, Student, AcademicSession, SchoolClass, StudentEnrollment

router = APIRouter(prefix="/api/fees", tags=["fees"])
types_router = APIRouter(prefix="/api/fee-types", tags=["fee-types"])
classfee_router = APIRouter(prefix="/api/class-fees", tags=["class-fees"])


class FeeTypeIn(BaseModel):
    name: str
    default_amount: float = 0
    is_recurring_monthly: bool = True
    is_active: bool = True


@types_router.get("")
def list_fee_types(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db) if False else None
    # fees.view or feetypes.manage
    return [{"id": f.id, "name": f.name, "default_amount": float(f.default_amount or 0),
             "is_recurring_monthly": f.is_recurring_monthly, "is_active": f.is_active} for f in db.query(FeeType).order_by(FeeType.name).all()]


@types_router.post("")
def create_fee_type(data: FeeTypeIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db)
    f = FeeType(**data.model_dump())
    db.add(f); db.commit(); db.refresh(f)
    return {"id": f.id}


@types_router.post("/{fid}")
def update_fee_type(fid: int, data: FeeTypeIn, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db)
    f = db.get(FeeType, fid)
    if not f:
        raise HTTPException(404)
    for k, v in data.model_dump().items():
        setattr(f, k, v)
    db.commit()
    return {"ok": True}


@types_router.post("/{fid}/status")
def toggle_fee_type(fid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db)
    f = db.get(FeeType, fid)
    if not f:
        raise HTTPException(404)
    f.is_active = not f.is_active
    db.commit()
    return {"is_active": f.is_active}


@types_router.post("/{fid}/delete")
def delete_fee_type(fid: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db)
    f = db.get(FeeType, fid)
    if not f:
        raise HTTPException(404)
    db.delete(f); db.commit()
    return {"ok": True}


# class fee config
@classfee_router.get("/{class_id}")
def get_class_fee_config(class_id: int, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    rows = db.query(ClassFeeType).filter(ClassFeeType.class_id == class_id, ClassFeeType.academic_session_id == session_id).all()
    return [{"id": r.id, "fee_type_id": r.fee_type_id, "amount": float(r.amount or 0)} for r in rows]


@classfee_router.post("/{class_id}")
def save_class_fee_config(class_id: int, items: List[dict], session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("feetypes.manage")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    # upsert
    for it in items:
        ft_id = it["fee_type_id"]
        amt = it["amount"]
        existing = db.query(ClassFeeType).filter(ClassFeeType.class_id == class_id, ClassFeeType.academic_session_id == session_id, ClassFeeType.fee_type_id == ft_id).first()
        if existing:
            existing.amount = amt
        else:
            db.add(ClassFeeType(class_id=class_id, academic_session_id=session_id, fee_type_id=ft_id, amount=amt))
    db.commit()
    return {"ok": True}


# fee records
@router.get("")
def fees_index(user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.view")(user, db)
    # class-wise summary: list classes with counts
    classes = db.query(SchoolClass).filter(SchoolClass.is_active == True).all()
    return [{"id": c.id, "name": c.name, "section": c.section} for c in classes]


@router.get("/students/{student_id}")
def student_fees(student_id: int, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.view")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    records = db.query(FeeRecord).filter(FeeRecord.student_id == student_id, FeeRecord.academic_session_id == session_id).order_by(FeeRecord.month, FeeRecord.fee_type_id).all()
    s = db.get(Student, student_id)
    return {
        "student": {"id": s.id, "name": s.name, "student_code": s.student_code} if s else None,
        "records": [{
            "id": r.id, "fee_type_id": r.fee_type_id, "fee_type_name": (db.get(FeeType, r.fee_type_id).name if db.get(FeeType, r.fee_type_id) else ""),
            "month": r.month, "year": r.year, "amount_due": float(r.amount_due or 0), "amount_paid": float(r.amount_paid or 0),
            "paid_date": str(r.paid_date) if r.paid_date else None, "status": r.status, "payment_method": r.payment_method, "notes": r.notes,
        } for r in records],
    }


@router.post("/students/{student_id}/generate")
def generate_fees(student_id: int, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.manage")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    # find student enrollment class
    enr = db.query(StudentEnrollment).filter(StudentEnrollment.student_id == student_id, StudentEnrollment.academic_session_id == session_id).first()
    if not enr:
        raise HTTPException(400, "No enrollment")
    # class fee types
    cfts = db.query(ClassFeeType).filter(ClassFeeType.class_id == enr.class_id, ClassFeeType.academic_session_id == session_id).all()
    created = 0
    for cft in cfts:
        ft = db.get(FeeType, cft.fee_type_id)
        recurring = ft.is_recurring_monthly if ft else True
        months = range(1, 13) if recurring else [1]
        for m in months:
            exists = db.query(FeeRecord).filter(FeeRecord.student_id == student_id, FeeRecord.fee_type_id == cft.fee_type_id, FeeRecord.month == m, FeeRecord.year == 2026).first()
            if exists:
                continue
            db.add(FeeRecord(student_id=student_id, fee_type_id=cft.fee_type_id, academic_session_id=session_id,
                             month=m, year=2026, amount_due=float(cft.amount or 0), status="due"))
            created += 1
    db.commit()
    return {"created": created}


@router.post("/students/{student_id}/charge")
def add_charge(student_id: int, fee_type_id: int, month: int, year: int, amount_due: float,
               user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.manage")(user, db)
    cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
    session_id = cs.id if cs else 1
    r = FeeRecord(student_id=student_id, fee_type_id=fee_type_id, academic_session_id=session_id,
                  month=month, year=year, amount_due=amount_due, status="due")
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id}


@router.get("/records/{record_id}/edit")
def edit_charge(record_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.manage")(user, db)
    r = db.get(FeeRecord, record_id)
    if not r:
        raise HTTPException(404)
    return {"id": r.id, "amount_due": float(r.amount_due or 0), "amount_paid": float(r.amount_paid or 0),
            "status": r.status, "payment_method": r.payment_method, "notes": r.notes, "paid_date": str(r.paid_date) if r.paid_date else None}


@router.post("/records/{record_id}")
def update_charge(record_id: int, amount_due: float, notes: Optional[str] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.manage")(user, db)
    r = db.get(FeeRecord, record_id)
    if not r:
        raise HTTPException(404)
    r.amount_due = amount_due
    r.notes = notes
    db.commit()
    return {"ok": True}


@router.post("/records/{record_id}/pay")
def pay(record_id: int, amount_paid: float, payment_method: Optional[str] = None, paid_date: Optional[date] = None,
        user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.manage")(user, db)
    r = db.get(FeeRecord, record_id)
    if not r:
        raise HTTPException(404)
    r.amount_paid = (r.amount_paid or 0) + amount_paid
    r.paid_date = paid_date or date.today()
    r.payment_method = payment_method
    if r.amount_paid >= r.amount_due:
        r.status = "paid"
    elif r.amount_paid > 0:
        r.status = "partial"
    db.commit()
    return {"status": r.status, "amount_paid": float(r.amount_paid)}


@router.post("/records/{record_id}/delete")
def delete_charge(record_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.manage")(user, db)
    r = db.get(FeeRecord, record_id)
    if not r:
        raise HTTPException(404)
    db.delete(r); db.commit()
    return {"ok": True}


@router.get("/classes/{class_id}/export")
def export_class_fees(class_id: int, session_id: Optional[int] = None, user=Depends(get_current_user), db: Session = Depends(get_db)):
    require_permission("fees.view")(user, db)
    if not session_id:
        cs = db.query(AcademicSession).filter(AcademicSession.is_current == True).first()
        session_id = cs.id if cs else 1
    # students in class
    from app.models import StudentEnrollment
    enrs = db.query(StudentEnrollment).filter(StudentEnrollment.class_id == class_id, StudentEnrollment.academic_session_id == session_id, StudentEnrollment.status == "active").all()
    out = []
    for e in enrs:
        s = db.get(Student, e.student_id)
        recs = db.query(FeeRecord).filter(FeeRecord.student_id == s.id, FeeRecord.academic_session_id == session_id).all()
        total_due = sum(float(r.amount_due or 0) for r in recs)
        total_paid = sum(float(r.amount_paid or 0) for r in recs)
        out.append({"student_id": s.id, "name": s.name, "roll_number": e.roll_number, "total_due": total_due, "total_paid": total_paid, "balance": total_due - total_paid})
    return {"rows": out}
