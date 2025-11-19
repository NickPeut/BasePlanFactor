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

    def add_child(self, name: str):
        child = GoalNode(name, self.level + 1, self)
        self.children.append(child)
        return child


def serialize_tree(node: GoalNode) -> List[Dict]:
    data = [{
        "id": node.id,
        "name": node.name,
        "parent": node.parent.id if node.parent else None,
        "level": node.level
    }]
    for ch in node.children:
        data.extend(serialize_tree(ch))
    return data


def collect_goals(node: GoalNode):
    items = [node]
    for ch in node.children:
        items.extend(collect_goals(ch))
    return items
