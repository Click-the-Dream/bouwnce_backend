from sqlalchemy import Column, String

from app.models.basemodel import BaseModel


class Waitlist(BaseModel):
    __tablename__ = "waitlists"

    email = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    institution = Column(String, nullable=False)
