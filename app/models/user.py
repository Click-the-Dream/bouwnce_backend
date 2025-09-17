from sqlalchemy import Column, String, Enum, Boolean
from sqlalchemy.orm import relationship
from app.models import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(Enum("user", "admin"), default="user")
    
    # One To One Relationship
    buisiness_info = relationship("BusinessInfo", back_populates="user", cascade="all, delete-orphan", uselist=False)
    contact_info = relationship("ContactInfo", back_populates="user", cascade="all, delete-orphan", uselist=False)
    store_info = relationship("StoreInfo", back_populates="user", cascade="all, delete-orphan", uselist=False)
    payout = relationship("Payout", back_populates="user", cascade="all, delete-orphan", uselist=False)
    shipment_info = relationship("ShipmentInfo", back_populates="user", cascade="all, delete-orphan", uselist=False)
    store_info = relationship("StoreInfo", back_populates="user", cascade="all, delete-orphan", uselist=False)
    verification = relationship("Verification", back_populates="user", cascade="all, delete-orphan", uselist=False)