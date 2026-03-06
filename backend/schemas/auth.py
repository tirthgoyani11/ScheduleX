# schemas/auth.py
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    full_name: str
    college_id: str
    dept_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RegisterRequest(BaseModel):
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")
    full_name: str = Field(..., min_length=2, description="Full name")
    role: str = Field("super_admin", description="User role: super_admin, dept_admin, faculty")
    college_name: str | None = Field(None, description="College name (creates new college)")
    college_id: str | None = Field(None, description="Existing college ID")
    dept_name: str | None = Field(None, description="Department name (creates new department)")
    dept_id: str | None = Field(None, description="Department ID (required for dept_admin/faculty)")
    phone: str | None = Field(None, description="Phone number for WhatsApp")


class UserResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    college_id: str
    dept_id: str | None
    is_active: bool

    model_config = {"from_attributes": True}
