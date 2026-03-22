from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: Optional[str] = "cliente"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: bool # <--- Agregar esto

class UserOut(UserBase):
    id: int
    created_at: datetime
    is_active: bool # <--- Agregar esto
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str  # <--- ESTO ES VITAL
    user_id: int