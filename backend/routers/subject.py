# routers/subject.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, require_any_admin, get_current_user
from models.user import User, UserRole
from models.subject import Subject
from schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.post("", response_model=SubjectResponse)
async def create_subject(
    request: SubjectCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new subject. Admin only."""
    target_dept_id = request.dept_id if (current_user.role == UserRole.SUPER_ADMIN and request.dept_id) else current_user.dept_id
    if not target_dept_id:
        raise HTTPException(status_code=400, detail="Department ID required")
    subject = Subject(
        dept_id=target_dept_id,
        name=request.name,
        subject_code=request.subject_code,
        semester=request.semester,
        credits=request.credits,
        weekly_periods=request.weekly_periods,
        lecture_hours=request.lecture_hours,
        lab_hours=request.lab_hours,
        needs_lab=request.needs_lab,
        batch_size=request.batch_size,
        batch=request.batch,
    )
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return SubjectResponse.model_validate(subject)


@router.get("", response_model=list[SubjectResponse])
async def list_subjects(
    semester: int | None = None,
    dept_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List subjects, optionally filtered by semester and department."""
    if current_user.role == UserRole.SUPER_ADMIN:
        query = select(Subject)
        if dept_id:
            query = query.where(Subject.dept_id == dept_id)
    else:
        query = select(Subject).where(Subject.dept_id == current_user.dept_id)
    if semester:
        query = query.where(Subject.semester == semester)
    result = await db.execute(query)
    subjects = result.scalars().all()
    return [SubjectResponse.model_validate(s) for s in subjects]


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a subject by ID."""
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role == UserRole.DEPT_ADMIN and subject.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot access subjects from other departments")
    return SubjectResponse.model_validate(subject)


@router.put("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: str,
    request: SubjectUpdate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a subject. Admin only."""
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role == UserRole.DEPT_ADMIN and subject.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot modify subjects from other departments")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subject, field, value)

    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return SubjectResponse.model_validate(subject)


@router.delete("/{subject_id}")
async def delete_subject(
    subject_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a subject. Admin only."""
    subject = await db.get(Subject, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    if current_user.role == UserRole.DEPT_ADMIN and subject.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot delete subjects from other departments")

    await db.delete(subject)
    await db.commit()
    return {"message": "Subject deleted"}
