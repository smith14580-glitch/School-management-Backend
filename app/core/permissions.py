PERMISSIONS = {
    "admin": ["*"],
    "madam": [
        "students.view","students.manage","classes.view","classes.manage","subjects.view","subjects.manage",
        "attendance.view","attendance.manage","tests.view","tests.manage","exams.view","exams.manage",
        "results.view","results.manage","teachers.view","teachers.manage","promotion.manage","reports.view",
        "whatsapp.send","timetable.view","timetable.manage","notices.view","notices.manage","calendar.view",
        "calendar.manage","activitylog.view","settings.view","sessions.view",
    ],
    "account": ["fees.view","fees.manage","feetypes.manage","salaries.view","salaries.manage"],
    "coordinator": [
        "students.view","classes.view","subjects.view","attendance.view","attendance.manage","tests.view",
        "exams.view","results.view","results.manage","teachers.view","reports.view","whatsapp.send",
        "timetable.view","notices.view","notices.manage","calendar.view",
    ],
    "teacher": [
        "students.view","classes.view","subjects.view","attendance.view","attendance.manage","tests.view",
        "tests.manage","exams.view","results.view","results.enter","reports.view","timetable.view",
        "notices.view","calendar.view",
    ],
}


def has_permission(role_slug: str, permission: str) -> bool:
    perms = PERMISSIONS.get(role_slug, [])
    if "*" in perms:
        return True
    return permission in perms
