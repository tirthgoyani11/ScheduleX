# routers/exam.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, require_any_admin, get_current_user
from models.user import User
from models.exam import ExamTimetable, ExamTimetableStatus
from schemas.exam import ExamTimetableCreate, ExamTimetableResponse
from schemas.common import JobResponse
import uuid

router = APIRouter(prefix="/exam", tags=["Exam"])


@router.post("/generate", response_model=JobResponse)
async def generate_exam_timetable(
    request: ExamTimetableCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Trigger exam timetable generation as a background job."""
    exam_tt = ExamTimetable(
        exam_tt_id=str(uuid.uuid4()),
        dept_id=current_user.dept_id,
        semester=request.semester,
        academic_year=request.academic_year,
        exam_period_start=request.exam_period_start,
        exam_period_end=request.exam_period_end,
        buffer_days=request.buffer_days,
        status=ExamTimetableStatus.DRAFT,
    )
    db.add(exam_tt)
    await db.commit()

    # TODO: Enqueue exam generation job in Phase 2
    return JobResponse(
        job_id=str(uuid.uuid4()),
        timetable_id=exam_tt.exam_tt_id,
        status="QUEUED",
    )


@router.get("/{exam_tt_id}", response_model=ExamTimetableResponse)
async def get_exam_timetable(
    exam_tt_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an exam timetable with entries."""
    result = await db.execute(
        select(ExamTimetable).where(ExamTimetable.exam_tt_id == exam_tt_id)
    )
    exam_tt = result.scalar_one_or_none()
    if not exam_tt:
        raise HTTPException(status_code=404, detail="Exam timetable not found")

    return ExamTimetableResponse(
        exam_tt_id=exam_tt.exam_tt_id,
        semester=exam_tt.semester,
        academic_year=exam_tt.academic_year,
        status=exam_tt.status.value,
        optimization_score=exam_tt.optimization_score,
        entries=[],  # Populated in Phase 2
    )
