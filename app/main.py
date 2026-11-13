from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth
from app.routers.classes import router as classes_router
from app.routers.class_students import router as class_students_router
from app.routers.students import router as students_router
from app.routers.teachers import router as teachers_router
from app.routers.fees import router as fees_router, types_router as fee_types_router, classfee_router as class_fees_router
from app.routers.attendance import router as attendance_router
from app.routers.daily_tests import router as tests_router
from app.routers.exams import router as exams_router, results_router as exam_results_router
from app.routers.salaries import router as salaries_router
from app.routers.users import router as users_router
from app.routers.sessions_settings import router as sessions_router, settings_router
from app.routers.notices_calendar_timetable import notices_router, calendar_router, timetable_router
from app.routers.promotion_reports_misc import promotion_router, reports_router, activity_router, backup_router, whatsapp_router

app = FastAPI(title=settings.app_name, debug=settings.app_debug)

origins = [o.strip() for o in settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(classes_router)
app.include_router(class_students_router)
app.include_router(students_router)
app.include_router(teachers_router)
app.include_router(fees_router)
app.include_router(fee_types_router)
app.include_router(class_fees_router)
app.include_router(attendance_router)
app.include_router(tests_router)
app.include_router(exams_router)
app.include_router(exam_results_router)
app.include_router(salaries_router)
app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(settings_router)
app.include_router(notices_router)
app.include_router(calendar_router)
app.include_router(timetable_router)
app.include_router(promotion_router)
app.include_router(reports_router)
app.include_router(activity_router)
app.include_router(backup_router)
app.include_router(whatsapp_router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
