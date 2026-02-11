from typing import Optional, List, Dict

from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint, Float
from sqlalchemy.orm import relationship

from db.base import Base

class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)

    parent_id = Column(Integer, ForeignKey("goals.id"), nullable=True)

    parent = relationship(
        "Goal",
        remote_side=[id],
        back_populates="children",
    )
    children = relationship(
        "Goal",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    scheme = relationship(
        "Scheme",
        back_populates="goals",
    )

class Classifier(Base):
    __tablename__ = "classifiers"

    id = Column(Integer, primary_key=True)

    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)

    name = Column(String, nullable=False)

    level = Column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("scheme_id", "level", "name", name="uq_classifier_scheme_level_name"),
    )

    scheme = relationship(
        "Scheme",
        back_populates="classifiers",
    )

    items = relationship(
        "ClassifierItem",
        back_populates="classifier",
        cascade="all, delete-orphan",
    )

class OseResult(Base):
    __tablename__ = "ose_results"

    id = Column(Integer, primary_key=True)

    scheme_id = Column(Integer, ForeignKey("schemes.id"), nullable=False)

    goal = Column(String, nullable=False)

    factor = Column(String, nullable=False)

    p = Column(Float, nullable=False)

    q = Column(Float, nullable=False)

    h = Column(Float, nullable=False)

    scheme = relationship(
        "Scheme",
        back_populates="ose_results",
    )

    __table_args__ = (
        UniqueConstraint("scheme_id", "goal", "factor", name="uq_ose_scheme_goal_factor"),
    )

class ClassifierItem(Base):
    __tablename__ = "classifier_items"

    id = Column(Integer, primary_key=True)

    classifier_id = Column(Integer, ForeignKey("classifiers.id"), nullable=False)

    value = Column(String, nullable=False)

    __table_args__ = (
        UniqueConstraint("classifier_id", "value", name="uq_classifier_item_value"),
    )

    classifier = relationship(
        "Classifier",
        back_populates="items",
    )

class GoalNode:
    _id_counter = 1

    def __init__(
        self,
        name: str,
        level: int = 1,
        parent: Optional["GoalNode"] = None,
    ):
        self.id = GoalNode._id_counter
        GoalNode._id_counter += 1

        self.name = name
        self.level = level
        self.parent = parent
        self.children: List["GoalNode"] = []

    def add_child(self, name: str) -> "GoalNode":
        child = GoalNode(
            name=name,
            level=self.level + 1,
            parent=self,
        )
        self.children.append(child)
        return child


def serialize_tree(node: GoalNode) -> List[Dict]:
    data = [{
        "id": node.id,
        "name": node.name,
        "parent": node.parent.id if node.parent else None,
        "level": node.level,
    }]
    for ch in node.children:
        data.extend(serialize_tree(ch))
    return data


def collect_goals(node: GoalNode) -> List[GoalNode]:
    items = [node]
    for ch in node.children:
        items.extend(collect_goals(ch))
    return items
