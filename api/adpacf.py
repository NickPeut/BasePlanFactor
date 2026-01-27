from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import GoalNode, serialize_tree, collect_goals


def handle_adpacf(ans: str) -> DialogResponse:
    text = ans.strip()

    if dialog.state == "ask_root":
        if not text:
            return DialogResponse(
                phase="adpacf",
                state="ask_root",
                question="Введите название главной цели:",
                tree=[],
            )

        if text.lower() in dialog.used_names:
            return DialogResponse(
                phase="adpacf",
                state="ask_root",
                question="Название уже существует. Введите другую главную цель:",
                tree=[],
            )

        root = GoalNode(text)
        dialog.root = root
        dialog.current_node = root

        dialog.used_names.add(text.lower())
        dialog.goal_by_name[text.lower()] = root

        dialog.state = "ask_add_subgoal"

        return DialogResponse(
            phase="adpacf",
            state="ask_add_subgoal",
            question=f"Добавить подцель для '{root.name}'? (да/нет)",
            tree=serialize_tree(root),
        )

    if dialog.state == "clf_pair_decide":
        answer_low = text.lower()

        if answer_low not in ("да", "нет"):
            x, y = dialog.clf_pairs[dialog.clf_pair_idx]
            return DialogResponse(
                phase="adpacf",
                state="clf_pair_decide",
                question=f"{x} / {y} — добавить как подцель? (да/нет)",
                tree=serialize_tree(dialog.root) if dialog.root else [],
            )

        parent = dialog.clf_parent_goal
        if not parent:
            dialog.state = "ask_add_subgoal"
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root) if dialog.root else [],
            )

        x, y = dialog.clf_pairs[dialog.clf_pair_idx]
        name = f"{x} / {y}"

        if answer_low == "да":
            if parent.level >= dialog.max_level:
                dialog.clf_pair_idx += 1
            else:
                if name.lower() not in dialog.used_names:
                    child = parent.add_child(name)
                    dialog.used_names.add(name.lower())
                    dialog.goal_by_name[name.lower()] = child
                dialog.clf_pair_idx += 1
        else:
            dialog.clf_pair_idx += 1

        if dialog.clf_pair_idx >= len(dialog.clf_pairs):
            dialog.clf_pairs = []
            dialog.clf_pair_idx = 0
            dialog.clf_parent_goal = None
            dialog.state = "ask_add_subgoal"
            dialog.current_node = parent
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Сочетания закончились. Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root) if dialog.root else [],
            )

        x, y = dialog.clf_pairs[dialog.clf_pair_idx]
        return DialogResponse(
            phase="adpacf",
            state="clf_pair_decide",
            question=f"{x} / {y} — добавить как подцель? (да/нет)",
            tree=serialize_tree(dialog.root) if dialog.root else [],
        )

    if dialog.state == "ask_add_subgoal":
        answer_low = text.lower()

        if answer_low == "да":
            if dialog.current_node.level >= dialog.max_level:
                return DialogResponse(
                    phase="adpacf",
                    state="ask_add_subgoal",
                    question=(
                        f"Достигнут максимальный уровень ({dialog.max_level}). "
                        f"Подцель для '{dialog.current_node.name}' добавить нельзя. "
                        f"Ответьте 'нет', чтобы вернуться к родительской цели или завершить ввод дерева."
                    ),
                    tree=serialize_tree(dialog.root),
                )

            dialog.state = "ask_subgoal_name"
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question=f"Введите название подцели для '{dialog.current_node.name}':",
                tree=serialize_tree(dialog.root),
            )

        if dialog.current_node.parent:
            dialog.current_node = dialog.current_node.parent
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        dialog.phase = "adpose"
        dialog.state = "ask_factor_name"
        dialog.goals_ordered = collect_goals(dialog.root)

        return DialogResponse(
            phase="adpose",
            state="ask_factor_name",
            question="Введите название фактора (или 'завершить'):",
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "ask_subgoal_name":
        if not text:
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question="Название не может быть пустым. Введите подцель:",
                tree=serialize_tree(dialog.root),
            )

        if text.lower() in dialog.used_names:
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question="Название уже используется. Введите другое название подцели:",
                tree=serialize_tree(dialog.root),
            )

        child = dialog.current_node.add_child(text)
        dialog.current_node = child

        dialog.used_names.add(text.lower())
        dialog.goal_by_name[text.lower()] = child

        dialog.state = "ask_add_subgoal"
        return DialogResponse(
            phase="adpacf",
            state="ask_add_subgoal",
            question=f"Добавить подцель для '{child.name}'? (да/нет)",
            tree=serialize_tree(dialog.root),
        )

    return DialogResponse(
        phase="adpacf",
        state="error",
        question="Неизвестное состояние в АДПАЦФ.",
        tree=serialize_tree(dialog.root) if dialog.root else [],
    )
