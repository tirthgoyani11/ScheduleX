# routers/websocket.py
"""
WebSocket endpoint for real-time job progress.
Client connects to /ws/jobs/{job_id} immediately after receiving job_id.
Server polls RQ job status every 2 seconds and pushes updates.
"""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import settings

router = APIRouter(tags=["WebSocket"])

# RQ uses fork() which is unavailable on Windows; import conditionally
try:
    from redis import Redis
    from rq.job import Job
    redis_conn = Redis.from_url(settings.REDIS_URL)
    RQ_AVAILABLE = True
except (ImportError, ValueError, OSError):
    redis_conn = None
    Job = None
    RQ_AVAILABLE = False


@router.websocket("/ws/jobs/{job_id}")
async def job_progress_ws(websocket: WebSocket, job_id: str):
    await websocket.accept()

    if not RQ_AVAILABLE:
        await websocket.send_text(json.dumps({
            "status": "ERROR",
            "error": "Job queue not available on this platform",
        }))
        await websocket.close()
        return

    try:
        while True:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                status = job.get_status()

                if status == "queued":
                    await websocket.send_text(json.dumps({
                        "status": "QUEUED",
                        "message": "Job is waiting in queue...",
                        "progress": 5,
                    }))

                elif status == "started":
                    meta = job.meta or {}
                    await websocket.send_text(json.dumps({
                        "status": "RUNNING",
                        "message": meta.get("message", "Solver is running..."),
                        "progress": meta.get("progress", 50),
                    }))

                elif status == "finished":
                    result = job.result
                    await websocket.send_text(json.dumps({
                        "status": "COMPLETE",
                        "result": result,
                        "progress": 100,
                    }))
                    break

                elif status == "failed":
                    await websocket.send_text(json.dumps({
                        "status": "FAILED",
                        "error": str(job.exc_info),
                        "progress": 0,
                    }))
                    break

            except Exception as e:
                await websocket.send_text(json.dumps({
                    "status": "ERROR",
                    "error": str(e),
                }))
                break

            await asyncio.sleep(2)

    except WebSocketDisconnect:
        pass
