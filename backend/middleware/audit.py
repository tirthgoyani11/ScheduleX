# middleware/audit.py
"""
FastAPI middleware that automatically logs every mutating request to audit_logs.
No route needs to manually call audit logging — this middleware handles all of it.
"""
from fastapi import Request
from models.audit import AuditLog
from database import AsyncSessionLocal
import uuid

AUDITED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

ROUTE_ACTION_MAP = {
    ("POST", "/timetable/generate"): ("CREATE_TIMETABLE", "timetable"),
    ("POST", "/timetable/{id}/publish"): ("PUBLISH_TIMETABLE", "timetable"),
    ("DELETE", "/timetable/{id}"): ("DELETE_TIMETABLE", "timetable"),
    ("POST", "/substitution/report-absence"): ("REPORT_ABSENCE", "substitution"),
    ("POST", "/faculty"): ("CREATE_FACULTY", "faculty"),
    ("DELETE", "/faculty/{id}"): ("DELETE_FACULTY", "faculty"),
    ("POST", "/exam/generate"): ("CREATE_EXAM_TIMETABLE", "exam"),
    ("POST", "/exam/{id}/publish"): ("PUBLISH_EXAM_TIMETABLE", "exam"),
}


async def audit_middleware(request: Request, call_next):
    response = await call_next(request)

    if request.method in AUDITED_METHODS and response.status_code < 400:
        try:
            user = getattr(request.state, "user", None)
            if user:
                action, entity_type = _resolve_action(request)
                log_entry = AuditLog(
                    log_id=str(uuid.uuid4()),
                    user_id=user.user_id,
                    user_role=user.role.value,
                    action=action,
                    entity_type=entity_type,
                    ip_address=request.client.host if request.client else None,
                )
                async with AsyncSessionLocal() as db:
                    db.add(log_entry)
                    await db.commit()
        except Exception:
            pass  # Never let audit logging break the response

    return response


def _resolve_action(request: Request) -> tuple[str, str]:
    path = request.url.path
    method = request.method
    for (m, p), (action, entity) in ROUTE_ACTION_MAP.items():
        if m == method and _path_matches(path, p):
            return action, entity
    return f"{method}_{path.replace('/', '_').upper()}", "unknown"


def _path_matches(actual: str, pattern: str) -> bool:
    pattern_parts = pattern.split("/")
    actual_parts = actual.split("/")
    if len(pattern_parts) != len(actual_parts):
        return False
    return all(
        p == a or p.startswith("{") for p, a in zip(pattern_parts, actual_parts)
    )
