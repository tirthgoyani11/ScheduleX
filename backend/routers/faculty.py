# routers/faculty.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, get_current_user, require_any_admin
from models.user import User, UserRole
from models.faculty import Faculty, FacultyGeneralBlock
from schemas.faculty import (
    FacultyCreate, FacultyUpdate, FacultyResponse,
    GeneralBlockCreate, GeneralBlockResponse,
)

router = APIRouter(prefix="/faculty", tags=["Faculty"])


@router.post("", response_model=FacultyResponse)
async def create_faculty(
    request: FacultyCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new faculty member. Admin only."""
    # Super admin must provide dept_id in request; dept admin uses own dept
    target_dept_id = request.dept_id if (current_user.role == UserRole.SUPER_ADMIN and request.dept_id) else current_user.dept_id
    if not target_dept_id:
        raise HTTPException(status_code=400, detail="Department ID required")
    faculty = Faculty(
        dept_id=target_dept_id,
        user_id=request.user_id,
        name=request.name,
        employee_id=request.employee_id,
        expertise=request.expertise,
        max_weekly_load=request.max_weekly_load,
        preferred_time=request.preferred_time,
    )
    db.add(faculty)
    await db.commit()
    await db.refresh(faculty)
    return FacultyResponse.model_validate(faculty)


@router.get("", response_model=list[FacultyResponse])
async def list_faculty(
    dept_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List faculty members.
    - Super admin: all faculty, or filter by dept_id query param
    - Dept admin: all faculty in their department
    - Faculty: own profile only
    """
    if current_user.role == UserRole.FACULTY:
        result = await db.execute(
            select(Faculty).where(Faculty.user_id == current_user.user_id)
        )
    elif current_user.role == UserRole.SUPER_ADMIN:
        query = select(Faculty)
        if dept_id:
            query = query.where(Faculty.dept_id == dept_id)
        result = await db.execute(query)
    else:
        result = await db.execute(
            select(Faculty).where(Faculty.dept_id == current_user.dept_id)
        )
    faculty_list = result.scalars().all()
    return [FacultyResponse.model_validate(f) for f in faculty_list]


@router.get("/{faculty_id}", response_model=FacultyResponse)
async def get_faculty(
    faculty_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a faculty member's details."""
    faculty = await db.get(Faculty, faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    # Scope check
    if current_user.role == UserRole.FACULTY and faculty.user_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Cannot access other faculty profiles")
    if current_user.role == UserRole.DEPT_ADMIN and faculty.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot access faculty from other departments")
    # Super admin can access any faculty
    return FacultyResponse.model_validate(faculty)


@router.put("/{faculty_id}", response_model=FacultyResponse)
async def update_faculty(
    faculty_id: str,
    request: FacultyUpdate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a faculty member. Admin only."""
    faculty = await db.get(Faculty, faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    if current_user.role == UserRole.DEPT_ADMIN and faculty.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot modify faculty from other departments")

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(faculty, field, value)

    db.add(faculty)
    await db.commit()
    await db.refresh(faculty)
    return FacultyResponse.model_validate(faculty)


@router.delete("/{faculty_id}")
async def delete_faculty(
    faculty_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a faculty member. Admin only."""
    faculty = await db.get(Faculty, faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    if current_user.role == UserRole.DEPT_ADMIN and faculty.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot delete faculty from other departments")

    await db.delete(faculty)
    await db.commit()
    return {"message": "Faculty deleted"}


# ── General Blocks ─────────────────────────────────────────────────

@router.post("/{faculty_id}/blocks", response_model=GeneralBlockResponse)
async def add_general_block(
    faculty_id: str,
    request: GeneralBlockCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Add a general block for a faculty member. Survives timetable deletions."""
    faculty = await db.get(Faculty, faculty_id)
    if not faculty:
        raise HTTPException(status_code=404, detail="Faculty not found")
    if faculty.dept_id != current_user.dept_id:
        raise HTTPException(status_code=403, detail="Cannot modify faculty from other departments")

    block = FacultyGeneralBlock(
        faculty_id=faculty_id,
        day=request.day,
        period=request.period,
        reason=request.reason,
    )
    db.add(block)
    await db.commit()
    await db.refresh(block)
    return GeneralBlockResponse.model_validate(block)


@router.delete("/{faculty_id}/blocks/{block_id}")
async def delete_general_block(
    faculty_id: str,
    block_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a general block."""
    block = await db.get(FacultyGeneralBlock, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    if block.faculty_id != faculty_id:
        raise HTTPException(status_code=400, detail="Block does not belong to this faculty")

    await db.delete(block)
    await db.commit()
    return {"message": "General block deleted"}
