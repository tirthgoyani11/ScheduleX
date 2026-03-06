# routers/auth.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_db, get_current_user
from models.user import User, UserRole
from schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest, RefreshResponse,
    RegisterRequest, UserResponse,
)
from utils.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
import jwt

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user and return JWT tokens."""
    result = await db.execute(
        select(User).where(User.email == request.email, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()

    token_data = {
        "sub": user.user_id,
        "role": user.role.value,
        "college_id": user.college_id,
        "dept_id": user.dept_id,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.user_id,
        role=user.role.value,
        full_name=user.full_name,
        college_id=user.college_id,
        dept_id=user.dept_id,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Issue a new access token using a valid refresh token."""
    try:
        payload = decode_token(request.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = payload.get("sub")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(
        select(User).where(User.user_id == user_id, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    token_data = {
        "sub": user.user_id,
        "role": user.role.value,
        "college_id": user.college_id,
        "dept_id": user.dept_id,
    }
    new_access_token = create_access_token(token_data)

    return RefreshResponse(access_token=new_access_token)


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint. Client should discard tokens."""
    return {"message": "Logged out successfully"}


@router.post("/signup", response_model=TokenResponse)
async def signup(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Public self-registration endpoint.
    Creates a new college, department, and super_admin user in one step.
    Used for first-time setup when no admin exists yet.
    """
    from models.college import College, Department

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create college if college_id not provided
    college_id = request.college_id
    if not college_id:
        college = College(
            name=request.college_name or (request.full_name + "'s College"),
        )
        db.add(college)
        await db.flush()
        college_id = college.college_id

    # Create department if dept_id not provided
    dept_id = request.dept_id
    if not dept_id and request.role in ("dept_admin", "super_admin"):
        dept = Department(
            college_id=college_id,
            name=request.dept_name or "Default Department",
            code="DEFAULT",
        )
        db.add(dept)
        await db.flush()
        dept_id = dept.dept_id

    # Validate role
    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=role,
        college_id=college_id,
        dept_id=dept_id,
        phone=request.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token_data = {
        "sub": user.user_id,
        "role": user.role.value,
        "college_id": user.college_id,
        "dept_id": user.dept_id,
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.user_id,
        role=user.role.value,
        full_name=user.full_name,
        college_id=user.college_id,
        dept_id=user.dept_id,
    )


@router.post("/register", response_model=UserResponse)
async def register_user(
    request: RegisterRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new user. Only super_admin can create users.
    Dept_admin can create faculty users in their own department.
    """
    # Permission check
    if current_user.role == UserRole.SUPER_ADMIN:
        # Super admin can create any user in their college
        if request.college_id != current_user.college_id:
            raise HTTPException(status_code=403, detail="Cannot create users in other colleges")
    elif current_user.role == UserRole.DEPT_ADMIN:
        # Dept admin can only create faculty in their department
        if request.role != "faculty":
            raise HTTPException(status_code=403, detail="Dept admin can only create faculty users")
        if request.dept_id != current_user.dept_id:
            raise HTTPException(status_code=403, detail="Cannot create users in other departments")
    else:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    # Validate role
    try:
        role = UserRole(request.role)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid role: {request.role}")

    user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        role=role,
        college_id=request.college_id,
        dept_id=request.dept_id,
        phone=request.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserResponse.model_validate(current_user)
