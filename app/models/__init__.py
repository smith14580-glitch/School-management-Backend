from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey,
    Integer, Numeric, SmallInteger, String, Text, UniqueConstraint, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _enum(*vals):
    return Enum(*vals, name=None)


# ---------- roles ----------
class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    users: Mapped[list["User"]] = relationship(back_populates="role")


# ---------- academic_sessions ----------
class AcademicSession(Base):
    __tablename__ = "academic_sessions"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    year_label: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- users ----------
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    email: Mapped[Optional[str]] = mapped_column(String(150), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    role: Mapped["Role"] = relationship(back_populates="users")
    teacher: Mapped[Optional["Teacher"]] = relationship(back_populates="user", uselist=False)


# ---------- settings ----------
class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    setting_key: Mapped[str] = mapped_column(String(60), nullable=False, unique=True)
    setting_value: Mapped[Optional[str]] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------- classes ----------
class SchoolClass(Base):
    __tablename__ = "classes"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    section: Mapped[Optional[str]] = mapped_column(String(10))
    class_order: Mapped[int] = mapped_column(SmallInteger, default=0)
    is_final_year: Mapped[bool] = mapped_column(Boolean, default=False)
    capacity: Mapped[Optional[int]] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped["AcademicSession"] = relationship()
    subjects: Mapped[list["Subject"]] = relationship(back_populates="school_class", cascade="all, delete-orphan")
    enrollments: Mapped[list["StudentEnrollment"]] = relationship(back_populates="school_class")


# ---------- subjects ----------
class Subject(Base):
    __tablename__ = "subjects"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(20))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    school_class: Mapped["SchoolClass"] = relationship(back_populates="subjects")


# ---------- students ----------
class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    father_guardian_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dob: Mapped[Optional[date]] = mapped_column(Date)
    gender: Mapped[Optional[str]] = mapped_column(String(10))
    contact: Mapped[Optional[str]] = mapped_column(String(25))
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(25))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    previous_school: Mapped[Optional[str]] = mapped_column(String(150))
    photo_path: Mapped[Optional[str]] = mapped_column(String(255))
    admission_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    enrollments: Mapped[list["StudentEnrollment"]] = relationship(back_populates="student", cascade="all, delete-orphan")
    documents: Mapped[list["StudentDocument"]] = relationship(back_populates="student", cascade="all, delete-orphan")


# ---------- student_enrollments ----------
class StudentEnrollment(Base):
    __tablename__ = "student_enrollments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    roll_number: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    enrolled_on: Mapped[date] = mapped_column(Date, nullable=False)
    ended_on: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="enrollments")
    school_class: Mapped["SchoolClass"] = relationship(back_populates="enrollments")
    session: Mapped["AcademicSession"] = relationship()


# ---------- student_documents ----------
class StudentDocument(Base):
    __tablename__ = "student_documents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    doc_type: Mapped[str] = mapped_column(String(60), nullable=False)
    file_path: Mapped[str] = mapped_column(String(255), nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship(back_populates="documents")


# ---------- fee_types ----------
class FeeType(Base):
    __tablename__ = "fee_types"
    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    default_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    is_recurring_monthly: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- class_fee_types ----------
class ClassFeeType(Base):
    __tablename__ = "class_fee_types"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    fee_type_id: Mapped[int] = mapped_column(ForeignKey("fee_types.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------- fee_records ----------
class FeeRecord(Base):
    __tablename__ = "fee_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    fee_type_id: Mapped[int] = mapped_column(ForeignKey("fee_types.id", ondelete="RESTRICT"), nullable=False)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    amount_due: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    amount_paid: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    paid_date: Mapped[Optional[date]] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(20), default="due")
    payment_method: Mapped[Optional[str]] = mapped_column(String(40))
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    student: Mapped["Student"] = relationship()
    fee_type: Mapped["FeeType"] = relationship()


# ---------- attendance ----------
class Attendance(Base):
    __tablename__ = "attendance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(150))
    marked_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------- daily_tests ----------
class DailyTest(Base):
    __tablename__ = "daily_tests"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    test_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    marks: Mapped[list["DailyTestMark"]] = relationship(back_populates="test", cascade="all, delete-orphan")


class DailyTestMark(Base):
    __tablename__ = "daily_test_marks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    daily_test_id: Mapped[int] = mapped_column(ForeignKey("daily_tests.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    marks_obtained: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    remarks: Mapped[Optional[str]] = mapped_column(String(150))

    test: Mapped["DailyTest"] = relationship(back_populates="marks")


# ---------- exams ----------
class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    term: Mapped[Optional[str]] = mapped_column(String(40))
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subjects: Mapped[list["ExamSubject"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    results: Mapped[list["ExamResult"]] = relationship(back_populates="exam", cascade="all, delete-orphan")


class ExamSubject(Base):
    __tablename__ = "exam_subjects"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))
    total_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=100)
    passing_marks: Mapped[float] = mapped_column(Numeric(6, 2), default=33)
    exam_date: Mapped[Optional[date]] = mapped_column(Date)
    exam_time: Mapped[Optional[str]] = mapped_column(String(10))

    exam: Mapped["Exam"] = relationship(back_populates="subjects")


class ExamResult(Base):
    __tablename__ = "exam_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    subject_id: Mapped[int] = mapped_column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    marks_obtained: Mapped[Optional[float]] = mapped_column(Numeric(6, 2))
    is_absent: Mapped[bool] = mapped_column(Boolean, default=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(150))
    entered_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    exam: Mapped["Exam"] = relationship(back_populates="results")

class ExamResultSummary(Base):
    __tablename__ = "exam_result_summary"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    total_obtained: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    total_possible: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    grade: Mapped[Optional[str]] = mapped_column(String(5))
    position: Mapped[Optional[int]] = mapped_column(SmallInteger)
    result_status: Mapped[str] = mapped_column(String(20), default="pending")
    attendance_present: Mapped[int] = mapped_column(SmallInteger, default=0)
    attendance_total: Mapped[int] = mapped_column(SmallInteger, default=0)
    attendance_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    finalized_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------- teachers ----------
class Teacher(Base):
    __tablename__ = "teachers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    employee_code: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    contact: Mapped[Optional[str]] = mapped_column(String(25))
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(25))
    email: Mapped[Optional[str]] = mapped_column(String(150))
    cnic: Mapped[Optional[str]] = mapped_column(String(20), unique=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(150))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    joining_date: Mapped[Optional[date]] = mapped_column(Date)
    photo_path: Mapped[Optional[str]] = mapped_column(String(255))
    basic_salary: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[Optional["User"]] = relationship(back_populates="teacher")
    assignments: Mapped[list["TeacherAssignment"]] = relationship(back_populates="teacher", cascade="all, delete-orphan")


class TeacherAssignment(Base):
    __tablename__ = "teacher_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subjects.id", ondelete="CASCADE"))
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    is_class_teacher: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    teacher: Mapped["Teacher"] = relationship(back_populates="assignments")


class TeacherSalary(Base):
    __tablename__ = "teacher_salaries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    basic_salary: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    allowances: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    deductions: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    net_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    paid_amount: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    paid_date: Mapped[Optional[date]] = mapped_column(Date)
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    recorded_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeacherAttendance(Base):
    __tablename__ = "teacher_attendance"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    remarks: Mapped[Optional[str]] = mapped_column(String(150))
    marked_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeacherSalaryHistory(Base):
    __tablename__ = "teacher_salary_history"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False)
    previous_salary: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    new_salary: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    increase_amount: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(String(255))
    changed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TeacherResignation(Base):
    __tablename__ = "teacher_resignations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, unique=True)
    resignation_date: Mapped[date] = mapped_column(Date, nullable=False)
    last_working_date: Mapped[Optional[date]] = mapped_column(Date)
    reason: Mapped[Optional[str]] = mapped_column(String(255))
    notice_period_days: Mapped[Optional[int]] = mapped_column(SmallInteger)
    settlement_status: Mapped[str] = mapped_column(String(20), default="pending")
    remarks: Mapped[Optional[str]] = mapped_column(String(255))
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeacherExitFeedback(Base):
    __tablename__ = "teacher_exit_feedback"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, unique=True)
    other_reason: Mapped[Optional[str]] = mapped_column(String(255))
    salary_feedback: Mapped[Optional[str]] = mapped_column(String(255))
    time_feedback: Mapped[Optional[str]] = mapped_column(String(255))
    management_feedback: Mapped[Optional[str]] = mapped_column(String(255))
    environment_feedback: Mapped[Optional[str]] = mapped_column(String(255))
    personal_feedback: Mapped[Optional[str]] = mapped_column(String(255))
    additional_feedback: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TeacherExitFeedbackReason(Base):
    __tablename__ = "teacher_exit_feedback_reasons"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exit_feedback_id: Mapped[int] = mapped_column(ForeignKey("teacher_exit_feedback.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(60), nullable=False)


# ---------- promotion_log ----------
class PromotionLog(Base):
    __tablename__ = "promotion_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="RESTRICT"), nullable=False)
    from_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"))
    to_class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("classes.id", ondelete="RESTRICT"))
    from_session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"))
    to_session_id: Mapped[Optional[int]] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"))
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(String(255))
    performed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- timetable ----------
class TimetableSlot(Base):
    __tablename__ = "timetable_slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="RESTRICT"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_time: Mapped[str] = mapped_column(String(8), nullable=False)
    end_time: Mapped[str] = mapped_column(String(8), nullable=False)
    subject_id: Mapped[Optional[int]] = mapped_column(ForeignKey("subjects.id", ondelete="SET NULL"))
    teacher_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teachers.id", ondelete="SET NULL"))
    room: Mapped[Optional[str]] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- notices ----------
class Notice(Base):
    __tablename__ = "notices"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    audience: Mapped[str] = mapped_column(String(20), default="all")
    role_id: Mapped[Optional[int]] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"))
    class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    publish_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    published_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- calendar ----------
class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_session_id: Mapped[int] = mapped_column(ForeignKey("academic_sessions.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(20), default="event")
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    class_id: Mapped[Optional[int]] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"))
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ---------- activity_log ----------
class ActivityLog(Base):
    __tablename__ = "activity_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    target_table: Mapped[Optional[str]] = mapped_column(String(60))
    target_id: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
