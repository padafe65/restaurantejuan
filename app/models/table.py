from sqlalchemy import Column, Integer, Enum
from sqlalchemy.orm import relationship
from app.database import Base

class Table(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    status = Column(Enum('libre', 'reservada', 'ocupada'), default='libre')

    reservations = relationship("Reservation", back_populates="table")