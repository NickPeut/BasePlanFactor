def print_tree(goal, level: int = 0) -> None:
    if goal is None:
        print("(empty)")
        return

    print("  " * level + "- " + goal.name)
    for child in goal.children:
        print_tree(child, level + 1)
