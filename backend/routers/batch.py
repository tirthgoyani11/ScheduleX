from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, get_current_user, require_any_admin
from models.batch import Batch
from models.user import User
from schemas.batch import BatchCreate, BatchResponse
import uuid

router = APIRouter(prefix="/batch", tags=["Batch"])


@router.get("", response_model=list[BatchResponse])
async def list_batches(
    semester: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Batch).where(Batch.dept_id == current_user.dept_id)
    if semester is not None:
        q = q.where(Batch.semester == semester)
    q = q.order_by(Batch.name)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("", response_model=BatchResponse, status_code=201)
async def create_batch(
    body: BatchCreate,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    batch = Batch(
        batch_id=str(uuid.uuid4()),
        dept_id=current_user.dept_id,
        semester=body.semester,
        name=body.name,
        size=body.size,
    )
    db.add(batch)
    await db.commit()
    await db.refresh(batch)
    return batch


@router.delete("/{batch_id}", status_code=204)
async def delete_batch(
    batch_id: str,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Batch).where(
            Batch.batch_id == batch_id,
            Batch.dept_id == current_user.dept_id,
        )
    )
    batch = result.scalar_one_or_none()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    await db.delete(batch)
    await db.commit()
