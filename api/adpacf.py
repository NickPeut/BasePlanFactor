from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import GoalNode, serialize_tree, collect_goals


def handle_adpacf(ans: str) -> DialogResponse:
    text = ans.strip()

    # === Ввод главной цели ===
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

    # === Вопрос: добавить подцель к текущей цели? ===
    if dialog.state == "ask_add_subgoal":
        answer_low = text.lower()

        if answer_low == "да":
            # проверяем глубину
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

        # любой ответ, отличный от "да" — считаем "нет"
        if dialog.current_node.parent:
            dialog.current_node = dialog.current_node.parent
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        # мы в корне и ответ "нет" → переходим к ОСЭ
        dialog.phase = "adpose"
        dialog.state = "ask_factor_name"
        dialog.goals_ordered = collect_goals(dialog.root)

        return DialogResponse(
            phase="adpose",
            state="ask_factor_name",
            question="Введите название фактора (или 'завершить'):",
            tree=serialize_tree(dialog.root),
        )

    # === Ввод названия подцели ===
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

    # fallback
    return DialogResponse(
        phase="adpacf",
        state="error",
        question="Неизвестное состояние в АДПАЦФ.",
        tree=serialize_tree(dialog.root) if dialog.root else [],
    )
