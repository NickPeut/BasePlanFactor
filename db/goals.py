from sqlalchemy.orm import Session, joinedload
from .goal import Goal, Classifier, ClassifierItem


def get_root_goal(session: Session) -> Goal | None:
    return session.query(Goal).filter(Goal.parent_id == None).first()


def get_goal_by_id(session: Session, goal_id: int) -> Goal | None:
    return session.query(Goal).filter(Goal.id == goal_id).first()


def get_all_goals(session: Session, scheme_id: int) -> list[Goal]:
    return session.query(Goal).filter(Goal.scheme_id == scheme_id).all()


def list_classifiers(session: Session, scheme_id: int, level: int | None = None) -> list[Classifier]:
    q = session.query(Classifier).filter(Classifier.scheme_id == scheme_id)
    if level is not None:
        q = q.filter(Classifier.level == level)
    return q.order_by(Classifier.level.asc(), Classifier.name.asc()).all()


def create_classifier(session: Session, scheme_id: int, name: str, level: int = 1) -> Classifier:
    clf = Classifier(
        scheme_id=scheme_id,
        name=name,
        level=level,
    )
    session.add(clf)
    session.commit()
    session.refresh(clf)
    return clf


def add_classifier_item(session: Session, classifier_id: int, value: str) -> ClassifierItem:
    item = ClassifierItem(
        classifier_id=classifier_id,
        value=value,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def get_classifier_with_items(session: Session, scheme_id: int, name: str, level: int = 1) -> Classifier | None:
    return (
        session.query(Classifier)
        .options(joinedload(Classifier.items))
        .filter(
            Classifier.scheme_id == scheme_id,
            Classifier.name == name,
            Classifier.level == level,
        )
        .first()
    )
