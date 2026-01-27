from sqlalchemy.orm import Session, joinedload

from .goal import Goal, Classifier, ClassifierItem, GoalNode


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


def get_classifier_with_items(session: Session, scheme_id: int, name: str, level: int | None = None) -> Classifier | None:
    q = (
        session.query(Classifier)
        .options(joinedload(Classifier.items))
        .filter(
            Classifier.scheme_id == scheme_id,
            Classifier.name == name,
        )
    )
    if level is not None:
        q = q.filter(Classifier.level == level)
    return q.first()


def delete_classifier(session: Session, scheme_id: int, name: str) -> bool:
    clf = (
        session.query(Classifier)
        .filter(
            Classifier.scheme_id == scheme_id,
            Classifier.name == name,
        )
        .first()
    )
    if not clf:
        return False
    session.delete(clf)
    session.commit()
    return True


def replace_goals_from_tree(session: Session, scheme_id: int, root: GoalNode | None) -> None:
    session.query(Goal).filter(
        Goal.scheme_id == scheme_id,
        Goal.parent_id != None,
    ).delete(synchronize_session=False)
    session.query(Goal).filter(
        Goal.scheme_id == scheme_id,
        Goal.parent_id == None,
    ).delete(synchronize_session=False)

    if not root:
        session.commit()
        return

    def _create(node: GoalNode, parent_id: int | None):
        g = Goal(name=node.name, scheme_id=scheme_id, parent_id=parent_id)
        session.add(g)
        session.flush()
        node.id = g.id
        for ch in getattr(node, "children", []) or []:
            _create(ch, g.id)

    _create(root, None)
    session.commit()
