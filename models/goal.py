from typing import Optional, List, Dict


class GoalNode:
    _id_counter = 1

    def __init__(self, name: str, level: int = 1, parent: Optional["GoalNode"] = None):
        self.id = GoalNode._id_counter
        GoalNode._id_counter += 1

        self.name = name
        self.level = level
        self.parent = parent
        self.children: List["GoalNode"] = []

    def add_child(self, name: str) -> "GoalNode":
        child = GoalNode(name=name, level=self.level + 1, parent=self)
        self.children.append(child)
        return child


def serialize_tree(node: GoalNode) -> List[Dict]:
    """Плоский список вершин дерева для фронтенда."""
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
    """Собираем все цели в один список (для обхода в ОСЭ)."""
    items = [node]
    for ch in node.children:
        items.extend(collect_goals(ch))
    return items
