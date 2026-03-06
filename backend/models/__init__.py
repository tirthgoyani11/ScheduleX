# models/__init__.py — Import all models so Alembic and SQLAlchemy can discover them
from models.college import College, Department
from models.user import User, UserRole
from models.faculty import Faculty, FacultyGeneralBlock
from models.subject import Subject
from models.room import Room, RoomType, Venue, VenueType
from models.timetable import Timetable, TimetableEntry, TimetableStatus, EntryType
from models.global_booking import GlobalBooking
from models.substitution import Substitution, SubstitutionRequest, SubstitutionStatus
from models.notification import NotificationLog, NotificationChannel, NotificationStatus, NotificationEventType
from models.exam import ExamTimetable, ExamEntry, InvigilatorAssignment, StudentExamEnrolment
from models.audit import AuditLog
from models.timeslot import TimeSlotConfig, SlotType

__all__ = [
    "College", "Department",
    "User", "UserRole",
    "Faculty", "FacultyGeneralBlock",
    "Subject",
    "Room", "RoomType", "Venue", "VenueType",
    "Timetable", "TimetableEntry", "TimetableStatus", "EntryType",
    "GlobalBooking",
    "Substitution", "SubstitutionRequest", "SubstitutionStatus",
    "NotificationLog", "NotificationChannel", "NotificationStatus", "NotificationEventType",
    "ExamTimetable", "ExamEntry", "InvigilatorAssignment", "StudentExamEnrolment",
    "AuditLog",
    "TimeSlotConfig", "SlotType",
]
