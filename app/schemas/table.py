from pydantic import BaseModel
from typing import Optional

class TableBase(BaseModel):
    number: int
    capacity: int
    status: str = "libre"

class TableCreate(TableBase):
    pass

class TableUpdate(BaseModel):
    number: Optional[int] = None
    capacity: Optional[int] = None
    status: Optional[str] = None

class TableOut(TableBase):
    id: int
    class Config:
        from_attributes = True