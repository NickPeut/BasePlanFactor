from sqlalchemy.orm import Session
from .goal import Goal


def get_root_goal(session: Session) -> Goal | None:
    return session.query(Goal).filter(Goal.parent_id == None).first()


def get_goal_by_id(session: Session, goal_id: int) -> Goal | None:
    return session.query(Goal).filter(Goal.id == goal_id).first()
