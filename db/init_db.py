from db.session import engine
from db.base import Base

def init_db() -> None:
    Base.metadata.create_all(bind=engine)
