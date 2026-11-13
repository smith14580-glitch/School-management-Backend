from sqlalchemy.orm import Session
from app.models import Teacher, TeacherAssignment, SchoolClass


def teacher_class_ids(user, db: Session) -> list[int] | None:
    """Return list of class ids a teacher may access, or None if unrestricted."""
    if user.role.slug if hasattr(user, "role") else None:
        pass
    # determine role slug via db
    from app.models import Role
    role = db.get(Role, user.role_id)
    if role.slug != "teacher":
        return None
    teacher = db.query(Teacher).filter(Teacher.user_id == user.id).first()
    if not teacher:
        return []
    ids = [a.class_id for a in db.query(TeacherAssignment).filter(TeacherAssignment.teacher_id == teacher.id).all()]
    return list(set(ids))


def scoped_classes_query(user, db: Session):
    q = db.query(SchoolClass)
    ids = teacher_class_ids(user, db)
    if ids is not None:
        if not ids:
            return q.filter(False)
        q = q.filter(SchoolClass.id.in_(ids))
    return q
