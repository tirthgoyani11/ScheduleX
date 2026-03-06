# core/scheduler/engine.py
"""
Main entry point for the timetable generation engine.
Called by the RQ background worker (workers/scheduler_worker.py).

Flow:
  1. Load all data from DB (faculty, subjects, rooms, global_bookings)
  2. Build CP-SAT variables (one Boolean var per faculty × subject × slot × room)
  3. Apply hard constraints (Section 7)
  4. Apply soft constraints with penalty weights (Section 7)
  5. Solve with time limit
  6. If OPTIMAL or FEASIBLE: persist entries to DB
  7. If INFEASIBLE: run explainer (Section 8), return diagnosis
  8. Calculate and store optimization_score
"""

from ortools.sat.python import cp_model
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid
import structlog

from models.timetable import Timetable, TimetableEntry, TimetableStatus, EntryType
from models.global_booking import GlobalBooking
from models.faculty import Faculty, FacultyGeneralBlock
from models.subject import Subject
from models.room import Room
from models.college import Department

from core.scheduler.variables import build_variables
from core.scheduler.hard_constraints import apply_hard_constraints
from core.scheduler.soft_constraints import apply_soft_constraints
from core.scheduler.explainer import explain_infeasibility
from core.scheduler.optimizer_score import calculate_score

log = structlog.get_logger()


async def generate_timetable(
    timetable_id: str,
    db: AsyncSession,
    config: dict,
) -> dict:
    """
    Run the CP-SAT solver to produce a timetable.

    Args:
        timetable_id: UUID of the Timetable row (already created by the router).
        db: Async SQLAlchemy session.
        config: Dict with keys:
            - faculty_subject_map: {faculty_id: [subject_id, ...]}
            - time_limit_seconds: int (default 120)

    Returns:
        {"status": "OPTIMAL"|"FEASIBLE"|"INFEASIBLE"|"UNKNOWN",
         "score": float, "entry_count": int, "diagnosis": dict|None}
    """
    log.info("generate_start", timetable_id=timetable_id)

    # ── 1. Load data ──────────────────────────────────────────────────────────
    data = await _load_scheduling_data(timetable_id, db, config)

    if not data["faculty"]:
        return _fail("No faculty found for this department.")
    if not data["subjects"]:
        return _fail("No subjects found for this department/semester.")
    if not data["rooms"]:
        return _fail("No rooms found for this college.")

    # ── 2. Build model & variables ────────────────────────────────────────────
    model = cp_model.CpModel()
    variables = build_variables(model, data)

    if not variables["assignments"]:
        return _fail(
            "No valid assignment variables could be created. "
            "Check faculty-subject mapping, room capacities, and lab availability."
        )

    # ── 3. Apply hard constraints ─────────────────────────────────────────────
    apply_hard_constraints(model, variables, data)

    # ── 4. Apply soft constraints & objective ─────────────────────────────────
    penalties = apply_soft_constraints(model, variables, data)
    if penalties:
        model.Minimize(sum(penalties))

    # ── 5. Solve ──────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.get("time_limit_seconds", 120)
    solver.parameters.num_workers = 4
    solver.parameters.log_search_progress = False

    status_code = solver.Solve(model)
    status_str = solver.StatusName(status_code)

    log.info(
        "solver_complete",
        timetable_id=timetable_id,
        status=status_str,
        wall_time=round(solver.WallTime(), 2),
        conflicts=solver.NumConflicts(),
        branches=solver.NumBranches(),
    )

    # ── 6. Handle result ──────────────────────────────────────────────────────
    if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        entries = await _persist_solution(solver, variables, data, timetable_id, db)
        score = await calculate_score(solver, penalties, data)

        # Save score to timetable row
        tt = data["timetable"]
        tt.optimization_score = score
        db.add(tt)
        await db.commit()

        return {
            "status": status_str,
            "score": score,
            "entry_count": len(entries),
            "diagnosis": None,
            "wall_time": round(solver.WallTime(), 2),
        }

    elif status_code == cp_model.INFEASIBLE:
        diagnosis = explain_infeasibility(data)
        return {
            "status": "INFEASIBLE",
            "score": 0.0,
            "entry_count": 0,
            "diagnosis": diagnosis,
            "wall_time": round(solver.WallTime(), 2),
        }

    else:
        return {
            "status": "UNKNOWN",
            "score": 0.0,
            "entry_count": 0,
            "diagnosis": {
                "type": "TIMEOUT",
                "message": (
                    "Solver did not reach a conclusion within the time limit. "
                    "Try reducing subjects or increasing time_limit_seconds."
                ),
            },
            "wall_time": round(solver.WallTime(), 2),
        }


# ── Private helpers ───────────────────────────────────────────────────────────

def _fail(message: str) -> dict:
    """Return a pre-solve failure result."""
    return {
        "status": "INFEASIBLE",
        "score": 0.0,
        "entry_count": 0,
        "diagnosis": {"type": "PRE_SOLVE_FAILURE", "message": message},
        "wall_time": 0.0,
    }


async def _load_scheduling_data(
    timetable_id: str, db: AsyncSession, config: dict
) -> dict:
    """Load all data needed by the solver from the database."""

    # Timetable
    tt_result = await db.execute(
        select(Timetable).where(Timetable.timetable_id == timetable_id)
    )
    timetable = tt_result.scalar_one()

    # Department (to get college_id)
    dept = await db.get(Department, timetable.dept_id)
    college_id = dept.college_id if dept else ""

    # Faculty in this department
    fac_result = await db.execute(
        select(Faculty).where(Faculty.dept_id == timetable.dept_id)
    )
    faculty_list = fac_result.scalars().all()

    # Subjects for this dept + semester
    sub_result = await db.execute(
        select(Subject).where(
            Subject.dept_id == timetable.dept_id,
            Subject.semester == timetable.semester,
        )
    )
    subject_list = sub_result.scalars().all()

    # Rooms in the same college
    room_result = await db.execute(
        select(Room).where(Room.college_id == college_id)
    )
    room_list = room_result.scalars().all()

    # Existing global bookings (slots already claimed by other departments)
    booking_result = await db.execute(
        select(GlobalBooking).where(GlobalBooking.college_id == college_id)
    )
    existing_bookings = booking_result.scalars().all()

    # General blocks for departmental faculty
    faculty_ids = [f.faculty_id for f in faculty_list]
    if faculty_ids:
        block_result = await db.execute(
            select(FacultyGeneralBlock).where(
                FacultyGeneralBlock.faculty_id.in_(faculty_ids)
            )
        )
        general_blocks = block_result.scalars().all()
    else:
        general_blocks = []

    faculty_subject_map_raw = config.get("faculty_subject_map", {})

    # API receives {faculty_id: [subject_ids]} from the frontend.
    # Convert to {subject_id: [faculty_ids]} for the solver internals.
    faculty_subject_map: dict[str, list[str]] = {}
    for fid, sids in faculty_subject_map_raw.items():
        for sid in sids:
            faculty_subject_map.setdefault(sid, []).append(fid)

    return {
        "timetable": timetable,
        "college_id": college_id,
        "faculty": faculty_list,
        "subjects": subject_list,
        "rooms": room_list,
        "existing_bookings": existing_bookings,
        "general_blocks": general_blocks,
        "faculty_subject_map": faculty_subject_map,
        "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"],
        "periods": list(range(1, 9)),  # 8 periods per day
    }


async def _persist_solution(
    solver: cp_model.CpSolver,
    variables: dict,
    data: dict,
    timetable_id: str,
    db: AsyncSession,
) -> list[TimetableEntry]:
    """Write solver solution to timetable_entries and global_bookings atomically."""
    entries: list[TimetableEntry] = []
    bookings: list[GlobalBooking] = []

    college_id = data["college_id"]
    dept_id = data["timetable"].dept_id

    # Look up subject batch for the entry
    subject_by_id = {s.subject_id: s for s in data["subjects"]}

    for (faculty_id, subject_id, room_id, day, period), var in variables["assignments"].items():
        if solver.Value(var) == 1:
            entry_id = str(uuid.uuid4())
            subject = subject_by_id.get(subject_id)

            entry = TimetableEntry(
                entry_id=entry_id,
                timetable_id=timetable_id,
                day=day,
                period=period,
                subject_id=subject_id,
                faculty_id=faculty_id,
                room_id=room_id,
                entry_type=EntryType.REGULAR,
                batch=subject.batch if subject else None,
            )
            booking = GlobalBooking(
                booking_id=str(uuid.uuid4()),
                college_id=college_id,
                dept_id=dept_id,
                timetable_entry_id=entry_id,
                day=day,
                period=period,
                faculty_id=faculty_id,
                room_id=room_id,
                booking_type="timetable",
            )
            entries.append(entry)
            bookings.append(booking)

    db.add_all(entries)
    db.add_all(bookings)

    # Update timetable status
    timetable = data["timetable"]
    timetable.status = TimetableStatus.DRAFT
    db.add(timetable)

    await db.commit()

    log.info(
        "solution_persisted",
        timetable_id=timetable_id,
        entries=len(entries),
        bookings=len(bookings),
    )
    return entries
