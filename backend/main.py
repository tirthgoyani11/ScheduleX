# main.py
"""
FastAPI application factory with lifespan, middleware, and router includes.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup: create tables (dev only — use Alembic in production).
    Shutdown: dispose engine.
    """
    if settings.APP_ENV == "development":
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Smart Timetable & Resource Optimization System",
    description="AI-based academic scheduling platform — CVM University",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS Middleware ─────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Audit & Rate Limit Middleware ──────────────────────────────
from middleware.audit import audit_middleware
from middleware.rate_limit import rate_limit_middleware

app.middleware("http")(audit_middleware)
app.middleware("http")(rate_limit_middleware)


# ── Import all models so Base.metadata knows about them ────────
import models  # noqa: F401


# ── Include Routers ────────────────────────────────────────────
from routers import auth, college, department, faculty, subject, room
from routers import timetable, substitution, notification, exam, nlq, analytics
from routers import websocket, webhook, timeslot

app.include_router(auth.router)
app.include_router(college.router)
app.include_router(department.router)
app.include_router(faculty.router)
app.include_router(subject.router)
app.include_router(room.router)
app.include_router(timetable.router)
app.include_router(timeslot.router)
app.include_router(substitution.router)
app.include_router(notification.router)
app.include_router(exam.router)
app.include_router(nlq.router)
app.include_router(analytics.router)
app.include_router(websocket.router)
app.include_router(webhook.router)


# ── Health Check ───────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }
