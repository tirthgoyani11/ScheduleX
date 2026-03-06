# routers/nlq.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_db, require_any_admin
from models.user import User
from schemas.nlq import NLQueryRequest, NLQueryResponse
from schemas.common import JobResponse
import uuid

router = APIRouter(prefix="/nlq", tags=["Natural Language Query"])


@router.post("/query", response_model=JobResponse)
async def query_nlq(
    request: NLQueryRequest,
    current_user: User = Depends(require_any_admin),
    db: AsyncSession = Depends(get_db),
):
    """Submit a natural language query about the timetable. Returns job_id."""
    # TODO: Enqueue NLQ processing job (Phase 2)
    return JobResponse(
        job_id=str(uuid.uuid4()),
        status="QUEUED",
    )
