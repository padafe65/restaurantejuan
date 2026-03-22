from sqlalchemy import Column, Integer, String, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name = Column(String(100), nullable=False)
    phone = Column(String(20))
    whatsapp = Column(String(20))
    address = Column(Text)

    user = relationship("User", back_populates="profile")
    reservations = relationship("Reservation", back_populates="customer")