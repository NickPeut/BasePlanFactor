from __future__ import annotations
from sqlalchemy.orm import Session
from db.scheme import Scheme


def list_schemes(session: Session) -> list[Scheme]:
    return session.query(Scheme).order_by(Scheme.id.desc()).all()


def create_scheme(session: Session, name: str) -> Scheme:
    s = Scheme(name=name)
    session.add(s)
    session.commit()
    session.refresh(s)
    return s


def delete_scheme(session: Session, scheme_id: int) -> None:
    s = session.query(Scheme).filter(Scheme.id == scheme_id).first()
    if not s:
        return
    session.delete(s)
    session.commit()
