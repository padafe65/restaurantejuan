from pydantic import BaseModel
from typing import Optional

class CustomerBase(BaseModel):
    full_name: str
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None

class CustomerCreate(CustomerBase):
    user_id: int

class CustomerUpdate(CustomerBase):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    whatsapp: Optional[str] = None
    address: Optional[str] = None

class CustomerOut(CustomerBase):
    id: int
    user_id: int
    class Config:
        from_attributes = True