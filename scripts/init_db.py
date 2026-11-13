import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import engine, Base
from app.models import *  # noqa
from sqlalchemy import text

# create all
Base.metadata.create_all(bind=engine)
print("tables created")

# seed
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import hash_password

db = SessionLocal()
try:
    from app.models import Role, AcademicSession, User, Setting, FeeType

    roles = [
        (1, "Admin", "admin", "Full access"),
        (2, "Madam", "madam", "Principal"),
        (3, "Account", "account", "Accountant"),
        (4, "Coordinator", "coordinator", "Coordinator"),
        (5, "Teacher", "teacher", "Teacher"),
    ]
    for rid, name, slug, desc in roles:
        if not db.get(Role, rid):
            db.add(Role(id=rid, name=name, slug=slug, description=desc))
    db.commit()

    if not db.query(AcademicSession).first():
        db.add(AcademicSession(id=1, year_label="2026-2027", start_date=__import__("datetime").date(2026,8,1), end_date=__import__("datetime").date(2027,5,31), is_current=True, is_locked=False))
        db.commit()

    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(id=1, role_id=1, name="System Administrator", username="admin", password_hash=hash_password("Admin@123"), status="active", must_change_password=True))
        db.commit()

    settings_seed = [
        ("school_name", "Your School Name"),
        ("school_tagline", ""),
        ("school_address", "School address line, City"),
        ("school_phone", ""),
        ("school_email", ""),
        ("school_logo_path", ""),
        ("currency_symbol", "Rs."),
        ("currency_code", "PKR"),
        ("date_format", "d-M-Y"),
        ("id_card_width_mm", "54"),
        ("id_card_height_mm", "85.6"),
        ("fee_overdue_rule", "end_of_month"),
    ]
    for k, v in settings_seed:
        if not db.query(Setting).filter(Setting.setting_key == k).first():
            db.add(Setting(setting_key=k, setting_value=v))
    db.commit()

    for fid, name, amt, recurring in [(1, "Monthly Fee", 0, True), (2, "Admission Fee", 0, False), (3, "Exam Fee", 0, False)]:
        if not db.get(FeeType, fid):
            db.add(FeeType(id=fid, name=name, default_amount=amt, is_recurring_monthly=recurring, is_active=True))
    db.commit()

    print("seeded")
except Exception as e:
    db.rollback()
    raise
finally:
    db.close()
print("done")
