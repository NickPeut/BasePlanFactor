from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from db.base import Base


class Scheme(Base):
    __tablename__ = "schemes"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    goals = relationship(
        "Goal",
        back_populates="scheme",
        cascade="all, delete-orphan",
    )
