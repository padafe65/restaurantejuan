from pydantic import BaseModel
from datetime import date, time, datetime
from typing import Optional

class ReservationBase(BaseModel):
    customer_id: int
    table_id: int
    reservation_date: date
    reservation_time: time
    pax: int
    status: str = "confirmada"

class ReservationCreate(ReservationBase):
    pass # Eliminamos user_id porque se saca del token

class ReservationUpdate(BaseModel):
    reservation_date: Optional[date] = None
    reservation_time: Optional[time] = None
    pax: Optional[int] = None
    status: Optional[str] = None

class ReservationOut(ReservationBase):
    id: int
    created_by_user_id: int
    created_at: datetime
    class Config:
        from_attributes = True