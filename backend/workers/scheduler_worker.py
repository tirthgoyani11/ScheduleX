# workers/scheduler_worker.py
"""
RQ worker for timetable generation.
Runs in a separate process: `rq worker timetable-queue`
Never import FastAPI dependencies here — this runs outside the web process.
NOTE: RQ uses fork() which is unavailable on Windows.
      On Windows, generation runs in-process as a fallback.
"""
import asyncio
from config import settings

try:
    from redis import Redis
    from rq import Queue
    redis_conn = Redis.from_url(settings.REDIS_URL)
    timetable_queue = Queue("timetable-queue", connection=redis_conn)
    RQ_AVAILABLE = True
except (ImportError, ValueError, OSError):
    redis_conn = None
    timetable_queue = None
    RQ_AVAILABLE = False


def enqueue_timetable_generation(
    timetable_id: str,
    faculty_subject_map: dict,
    time_limit_seconds: int = 120,
) -> str:
    """Enqueue a timetable generation job. Returns RQ job ID or timetable_id as fallback."""
    if not RQ_AVAILABLE or timetable_queue is None:
        # Fallback: return timetable_id as pseudo job-id
        return timetable_id

    job = timetable_queue.enqueue(
        _run_generation,
        kwargs={
            "timetable_id": timetable_id,
            "faculty_subject_map": faculty_subject_map,
            "time_limit_seconds": time_limit_seconds,
        },
        job_timeout=300,       # Max 5 min for very large problems
        result_ttl=3600,       # Keep result 1 hour
        failure_ttl=86400,     # Keep failures 24 hours for debugging
    )
    return job.id


def _run_generation(
    timetable_id: str,
    faculty_subject_map: dict,
    time_limit_seconds: int,
):
    """Synchronous wrapper — RQ runs this. Async code via asyncio.run()."""
    async def _async():
        from core.scheduler.engine import generate_timetable
        from database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            result = await generate_timetable(
                timetable_id=timetable_id,
                db=db,
                config={
                    "faculty_subject_map": faculty_subject_map,
                    "time_limit_seconds": time_limit_seconds,
                },
            )
            # Update timetable with result
            from models.timetable import Timetable
            tt = await db.get(Timetable, timetable_id)
            if tt:
                tt.optimization_score = result.get("score", 0)
                db.add(tt)
                await db.commit()
            return result

    return asyncio.run(_async())
