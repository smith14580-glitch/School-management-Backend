import pathlib, re
p = pathlib.Path(r"C:\Users\shahz\Downloads\SCHOOL-SYSTEM\backend\app\models\__init__.py")
s = p.read_text()
s = s.replace('    exam: Mapped[\\"Exam\\"] = relationship(back_populates=\\"results\\")', '    exam: Mapped["Exam"] = relationship(back_populates="results")')
p.write_text(s)
print("done")
print([l for l in s.splitlines() if 'exam: Mapped' in l])
