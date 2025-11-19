from core.dialog_state import dialog
from core.schemas import DialogResponse
from models.goal import GoalNode, serialize_tree, collect_goals


def handle_adpacf(ans: str):

    # === Главная цель ===
    if dialog.state == "ask_root":

        if ans.lower() in dialog.used_names:
            return DialogResponse(
                phase="adpacf",
                state="ask_root",
                question="Название уже существует. Введите другую главную цель:",
                tree=[]
            )

        root = GoalNode(ans)
        dialog.root = root
        dialog.current_node = root

        dialog.used_names.add(ans.lower())
        dialog.goal_by_name[ans.lower()] = root

        dialog.state = "ask_add_subgoal"

        return DialogResponse(
            phase="adpacf",
            state="ask_add_subgoal",
            question=f"Добавить подцель для '{ans}'? (да/нет)",
            tree=serialize_tree(root)
        )

    # === Добавить подцель? ===
    if dialog.state == "ask_add_subgoal":
        if ans.lower() == "да":

            if dialog.current_node.level >= dialog.max_level:
                return DialogResponse(
                    phase="adpacf",
                    state="ask_add_subgoal",
                    question=f"Максимальная глубина = {dialog.max_level}. Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                    tree=serialize_tree(dialog.root)
                )

            dialog.state = "ask_subgoal_name"
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question=f"Введите название подцели для '{dialog.current_node.name}':",
                tree=serialize_tree(dialog.root)
            )

        # ответ — НЕТ
        if dialog.current_node.parent:
            dialog.current_node = dialog.current_node.parent
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root)
            )

        # мы на корне → переходим к ОСЭ
        dialog.phase = "adpose"
        dialog.state = "ask_factor_name"
        dialog.goals_ordered = collect_goals(dialog.root)

        return DialogResponse(
            phase="adpose",
            state="ask_factor_name",
            question="Введите название фактора (или 'завершить'):",
            tree=serialize_tree(dialog.root)
        )

    # === Ввод названия подцели ===
    if dialog.state == "ask_subgoal_name":

        if ans.lower() in dialog.used_names:
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question="Название уже используется. Введите другое название подцели:",
                tree=serialize_tree(dialog.root)
            )

        child = dialog.current_node.add_child(ans)
        dialog.current_node = child

        dialog.used_names.add(ans.lower())
        dialog.goal_by_name[ans.lower()] = child

        dialog.state = "ask_add_subgoal"
        return DialogResponse(
            phase="adpacf",
            state="ask_add_subgoal",
            question=f"Добавить подцель для '{child.name}'? (да/нет)",
            tree=serialize_tree(dialog.root)
        )
