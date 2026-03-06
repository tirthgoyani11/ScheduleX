# core/scheduler/explainer.py
"""
When CP-SAT returns INFEASIBLE, this module diagnoses the root cause
and returns plain-English corrective suggestions.
NEVER show users a raw solver error — always explain it.
"""
from collections import defaultdict
import structlog

log = structlog.get_logger()


def explain_infeasibility(data: dict) -> dict:
    """
    Runs a lightweight diagnostic pass over the data to identify
    which constraint is causing infeasibility.
    Returns a structured diagnosis dict.
    """
    checks = [
        _check_faculty_overload,
        _check_no_valid_lab,
        _check_general_block_conflict,
        _check_room_capacity,
        _check_day_distribution,
        _check_too_many_subjects,
    ]

    for check_fn in checks:
        result = check_fn(data)
        if result:
            log.warning("infeasibility_diagnosed", diagnosis_type=result["type"])
            return result

    return {
        "type": "UNKNOWN",
        "message": (
            "Could not identify the specific conflict. "
            "Try removing one subject at a time to isolate the issue."
        ),
        "suggestions": [
            "Reduce the number of subjects for this semester",
            "Check faculty availability windows",
        ],
    }


def _check_faculty_overload(data: dict) -> dict | None:
    """Check if any faculty is assigned more periods than their max_weekly_load."""
    faculty_subject_map = data.get("faculty_subject_map", {})
    subject_by_id = {s.subject_id: s for s in data["subjects"]}

    for faculty in data["faculty"]:
        assigned_subjects = [
            subject_by_id[sid]
            for sid, fids in faculty_subject_map.items()
            if faculty.faculty_id in fids and sid in subject_by_id
        ]
        total_periods = sum(s.weekly_periods for s in assigned_subjects)
        if total_periods > faculty.max_weekly_load:
            return {
                "type": "FACULTY_OVERLOADED",
                "message": (
                    f"Prof. {faculty.name} is assigned {total_periods} periods/week "
                    f"but their maximum load is {faculty.max_weekly_load}."
                ),
                "affected_faculty": faculty.name,
                "assigned_load": total_periods,
                "max_load": faculty.max_weekly_load,
                "suggestions": [
                    f"Reduce subjects assigned to Prof. {faculty.name} "
                    f"by at least {total_periods - faculty.max_weekly_load} periods",
                    f"Increase Prof. {faculty.name}'s max_weekly_load in their profile",
                    "Redistribute subjects to other available faculty with matching expertise",
                ],
            }
    return None


def _check_no_valid_lab(data: dict) -> dict | None:
    """Check if lab subjects have at least one lab room with sufficient capacity."""
    lab_subjects = [s for s in data["subjects"] if s.needs_lab]
    lab_rooms = [r for r in data["rooms"] if r.room_type.value == "lab"]
    batches = data.get("batches", [])
    # Labs seat individual batches, not the whole division
    max_batch_size = max((b.size for b in batches), default=20)

    for subject in lab_subjects:
        valid_labs = [r for r in lab_rooms if r.capacity >= max_batch_size]
        if not valid_labs:
            return {
                "type": "NO_VALID_LAB",
                "message": (
                    f"Subject '{subject.name}' requires a lab room for "
                    f"{max_batch_size} students (per batch), but no lab with sufficient capacity exists."
                ),
                "affected_subject": subject.name,
                "required_capacity": max_batch_size,
                "available_labs": [
                    {"name": r.name, "capacity": r.capacity} for r in lab_rooms
                ],
                "suggestions": [
                    f"Add a lab room with capacity >= {max_batch_size} to the college resources",
                    f"Split the '{subject.name}' batch into two smaller groups",
                    "Contact the college admin to register a larger lab room",
                ],
            }
    return None


def _check_general_block_conflict(data: dict) -> dict | None:
    """Check if a faculty's general blocks leave enough slots for their assigned subjects."""
    faculty_subject_map = data.get("faculty_subject_map", {})
    subject_by_id = {s.subject_id: s for s in data["subjects"]}

    block_coverage: dict[str, set[tuple[str, int]]] = defaultdict(set)
    for block in data["general_blocks"]:
        block_coverage[block.faculty_id].add((block.day, block.period))

    total_slots = len(data["days"]) * len(data["periods"])

    for faculty in data["faculty"]:
        assigned_subjects = [
            subject_by_id[sid]
            for sid, fids in faculty_subject_map.items()
            if faculty.faculty_id in fids and sid in subject_by_id
        ]
        assigned_periods = sum(s.weekly_periods for s in assigned_subjects)
        blocked = len(block_coverage.get(faculty.faculty_id, set()))
        available_slots = total_slots - blocked

        if assigned_periods > available_slots:
            return {
                "type": "GENERAL_BLOCK_CONFLICT",
                "message": (
                    f"Prof. {faculty.name} has {blocked} general blocks, "
                    f"leaving only {available_slots} available slots, "
                    f"but needs {assigned_periods} slots for their assigned subjects."
                ),
                "affected_faculty": faculty.name,
                "blocked_slots": blocked,
                "available_slots": available_slots,
                "required_slots": assigned_periods,
                "suggestions": [
                    f"Remove some general blocks for Prof. {faculty.name}",
                    f"Reduce the number of subjects assigned to Prof. {faculty.name}",
                    "Assign some subjects to other qualified faculty members",
                ],
            }
    return None


def _check_room_capacity(data: dict) -> dict | None:
    """Check if every subject has at least one room that can accommodate its students."""
    batches = data.get("batches", [])
    max_batch_size = max((b.size for b in batches), default=20)

    for subject in data["subjects"]:
        if subject.needs_lab:
            # Labs seat individual batches
            required = max_batch_size
            valid_rooms = [
                r for r in data["rooms"]
                if r.room_type.value == "lab" and r.capacity >= required
            ]
        else:
            # Classrooms seat the full division
            required = subject.batch_size
            valid_rooms = [
                r for r in data["rooms"]
                if r.room_type.value == "classroom" and r.capacity >= required
            ]
        if not valid_rooms:
            return {
                "type": "ROOM_CAPACITY_EXCEEDED",
                "message": (
                    f"No room can accommodate the {required} students "
                    f"in '{subject.name}'."
                ),
                "affected_subject": subject.name,
                "required_capacity": required,
                "largest_available": max(
                    (r.capacity for r in data["rooms"]), default=0
                ),
                "suggestions": [
                    "Register a larger room in the college resources",
                    f"Split the '{subject.name}' batch into smaller groups",
                    "Check if a room's capacity has been entered incorrectly",
                ],
            }
    return None


def _check_day_distribution(data: dict) -> dict | None:
    """Check if the schedule has enough days for subjects that need multi-day distribution."""
    available_days = len(data["days"])
    for subject in data["subjects"]:
        if subject.credits >= 3 and subject.weekly_periods >= 3:
            if available_days < 2:
                return {
                    "type": "DAY_DISTRIBUTION_FAIL",
                    "message": (
                        f"Subject '{subject.name}' requires classes on at least 2 days, "
                        f"but the schedule only has {available_days} working day(s)."
                    ),
                    "suggestions": [
                        "Add more working days to the schedule configuration"
                    ],
                }
    return None


def _check_too_many_subjects(data: dict) -> dict | None:
    """Check if total teaching periods exceed total faculty capacity."""
    total_periods_required = sum(s.weekly_periods for s in data["subjects"])
    total_faculty_capacity = sum(f.max_weekly_load for f in data["faculty"])

    if total_periods_required > total_faculty_capacity:
        return {
            "type": "INSUFFICIENT_FACULTY_CAPACITY",
            "message": (
                f"Semester requires {total_periods_required} teaching periods/week "
                f"but total faculty capacity is {total_faculty_capacity}."
            ),
            "required": total_periods_required,
            "available": total_faculty_capacity,
            "suggestions": [
                "Add more faculty members to the department",
                "Increase max_weekly_load for existing faculty (check labour policies)",
                "Remove or merge some subjects for this semester",
            ],
        }
    return None
