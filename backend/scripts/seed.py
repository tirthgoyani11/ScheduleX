# scripts/seed.py
"""
Seed the database with initial data:
  - Default college (CVM University)
  - Default department (Computer Engineering)
  - Super admin user

Usage: python scripts/seed.py
"""
import asyncio
import sys
import os

# Add parent directory to path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, Base, AsyncSessionLocal
from models.college import College, Department
from models.user import User, UserRole
from utils.security import hash_password
import uuid


async def seed():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        # Check if already seeded
        from sqlalchemy import select

        existing = await db.execute(select(College).limit(1))
        if existing.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # College
        college_id = str(uuid.uuid4())
        college = College(
            college_id=college_id,
            name="CVM University",
            affiliation="CVM",
            city="Anand",
        )
        db.add(college)

        # Department
        dept_id = str(uuid.uuid4())
        department = Department(
            dept_id=dept_id,
            college_id=college_id,
            name="Computer Engineering",
            code="CE",
        )
        db.add(department)

        # Super Admin
        admin = User(
            user_id=str(uuid.uuid4()),
            email="admin@cvmu.edu.in",
            hashed_password=hash_password("admin123"),
            full_name="System Admin",
            role=UserRole.SUPER_ADMIN,
            college_id=college_id,
            dept_id=dept_id,
        )
        db.add(admin)

        # Dept Admin for testing
        dept_admin = User(
            user_id=str(uuid.uuid4()),
            email="hod.ce@cvmu.edu.in",
            hashed_password=hash_password("hod123"),
            full_name="HOD Computer Engineering",
            role=UserRole.DEPT_ADMIN,
            college_id=college_id,
            dept_id=dept_id,
        )
        db.add(dept_admin)

        await db.commit()
        print("Seed data created successfully!")
        print(f"  College: CVM University (ID: {college_id})")
        print(f"  Department: Computer Engineering (ID: {dept_id})")
        print(f"  Super Admin: admin@cvmu.edu.in / admin123")
        print(f"  Dept Admin: hod.ce@cvmu.edu.in / hod123")


if __name__ == "__main__":
    # Import all models so metadata knows about them
    import models  # noqa: F401

    asyncio.run(seed())
