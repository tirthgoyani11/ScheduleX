# routers/department.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, get_current_user, require_super_admin
from models.user import User
from models.college import Department
from schemas.college import DepartmentCreate, DepartmentResponse

router = APIRouter(prefix="/departments", tags=["Departments"])


@router.get("/{dept_id}", response_model=DepartmentResponse)
async def get_department(
    dept_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get department details."""
    department = await db.get(Department, dept_id)
    if not department:
        raise HTTPException(status_code=404, detail="Department not found")
    if department.college_id != current_user.college_id:
        raise HTTPException(status_code=403, detail="Cannot access departments from other colleges")
    return DepartmentResponse.model_validate(department)
