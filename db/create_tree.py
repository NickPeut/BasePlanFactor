from db.session import SessionLocal, engine
from db.base import Base
from db.scheme import Scheme

Base.metadata.create_all(bind=engine)

session = SessionLocal()
try:
    scheme = Scheme(name="Default")
    session.add(scheme)
    session.flush()
    session.commit()
finally:
    session.close()
