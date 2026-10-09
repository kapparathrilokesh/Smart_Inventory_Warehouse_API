from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    role: UserRole = UserRole.WAREHOUSE_STAFF
    warehouse_id: int | None = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    role: UserRole
    warehouse_id: int | None
    is_active: bool

    class Config:
        from_attributes = True