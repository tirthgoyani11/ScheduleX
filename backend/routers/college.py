# routers/college.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, require_super_admin, get_current_user
from models.college import College, Department
from models.user import User, UserRole
from schemas.college import CollegeCreate, CollegeResponse, DepartmentCreate, DepartmentResponse

router = APIRouter(prefix="/colleges", tags=["Colleges"])


@router.post("", response_model=CollegeResponse)
async def create_college(
    request: CollegeCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new college. Super admin only."""
    college = College(
        name=request.name,
        affiliation=request.affiliation,
        city=request.city,
    )
    db.add(college)
    await db.commit()
    await db.refresh(college)
    return CollegeResponse.model_validate(college)


@router.get("/{college_id}", response_model=CollegeResponse)
async def get_college(
    college_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get college details."""
    if current_user.college_id != college_id:
        raise HTTPException(status_code=403, detail="Cannot access other colleges")

    result = await db.execute(select(College).where(College.college_id == college_id))
    college = result.scalar_one_or_none()
    if not college:
        raise HTTPException(status_code=404, detail="College not found")
    return CollegeResponse.model_validate(college)


@router.post("/{college_id}/departments", response_model=DepartmentResponse)
async def create_department(
    college_id: str,
    request: DepartmentCreate,
    current_user: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new department in a college. Super admin only."""
    if current_user.college_id != college_id:
        raise HTTPException(status_code=403, detail="Cannot manage other colleges")

    department = Department(
        college_id=college_id,
        name=request.name,
        code=request.code,
    )
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return DepartmentResponse.model_validate(department)


@router.get("/{college_id}/departments", response_model=list[DepartmentResponse])
async def list_departments(
    college_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List departments in a college."""
    if current_user.college_id != college_id:
        raise HTTPException(status_code=403, detail="Cannot access other colleges")

    result = await db.execute(
        select(Department).where(Department.college_id == college_id)
    )
    departments = result.scalars().all()
    return [DepartmentResponse.model_validate(d) for d in departments]
