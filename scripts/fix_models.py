import pathlib, re
p = pathlib.Path(r"C:\Users\shahz\Downloads\SCHOOL-SYSTEM\backend\app\models\__init__.py")
s = p.read_text()
s2 = re.sub(r"(    updated_at: Mapped\[datetime\] = mapped_column\(DateTime, default=datetime\.utcnow, onupdate=datetime\.utcnow\)\n)(\n+)(class ExamResultSummary\(Base\):)",
            r"\1\n    exam: Mapped[\"Exam\"] = relationship(back_populates=\"results\")\n\n\3", s, count=1)
assert s2 != s
p.write_text(s2)
print("ok")
