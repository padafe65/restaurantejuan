from sqlalchemy import Column, Integer, String, Enum, TIMESTAMP, Boolean
from sqlalchemy.orm import relationship
from app.database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum('admin', 'mesero', 'cliente'), default='cliente')
    created_at = Column(TIMESTAMP, default=datetime.datetime.utcnow)
    is_active = Column(Boolean, default=True)
    profile = relationship("Customer", back_populates="user", uselist=False)
    reservations_created = relationship("Reservation", back_populates="creator")
    logs = relationship("AuditLog", back_populates="operator")