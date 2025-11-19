import re
from core.dialog_state import dialog
from core.schemas import DialogResponse
from models.goal import serialize_tree


def try_parse_edit_command(text: str):
    t = text.lower().strip()

    # переименовать цель
    m = re.match(r'измени цель\s+"(.+?)"\s+на\s+"(.+?)"$', t)
    if m:
        return ("rename_goal", m.group(1), m.group(2))

    # переименовать фактор
    m = re.match(r'измени фактор\s+"(.+?)"\s+на\s+"(.+?)"$', t)
    if m:
        return ("rename_factor", m.group(1), m.group(2))

    # удаление цели
    m = re.match(r'удали цель\s+"(.+?)"$', t)
    if m:
        return ("delete_goal", m.group(1))

    # удаление фактора
    m = re.match(r'удали фактор\s+"(.+?)"$', t)
    if m:
        return ("delete_factor", m.group(1))

    # универсальное удаление
    m = re.match(r'удали\s+"(.+?)"$', t)
    if m:
        return ("delete_auto", m.group(1))

    # добавить подцель
    m = re.match(r'добавь\s+"(.+?)"\s+как подцель\s+"(.+?)"$', t)
    if m:
        return ("add_subgoal", m.group(1), m.group(2))

    # перейти вперёд
    if t in ["пропустить", "продолжить"]:
        return ("skip",)

    # завершить диалог
    if t in ["завершить", "конец"]:
        return ("finish",)

    return None


def edit_response(msg: str):
    return DialogResponse(
        phase=dialog.phase,
        state=dialog.state,
        question=f"Продолжайте:",
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
        message=msg
    )


# сама обработка команды:
def handle_edit_command(cmd):

    kind = cmd[0]

    # --- пропустить ---
    if kind == "skip":
        return edit_response("Шаг пропущен.")

    # --- завершить фазу ОСЭ ---
    if kind == "finish":
        dialog.state = "finish_ose"
        return edit_response("Диалог завершён.")

    # --- переименование цели ---
    if kind == "rename_goal":
        old, new = cmd[1], cmd[2]

        if old.lower() not in dialog.goal_by_name:
            return edit_response(f"Цель '{old}' не найдена.")

        if new.lower() in dialog.used_names:
            return edit_response("Название уже занято.")

        node = dialog.goal_by_name.pop(old.lower())
        node.name = new

        dialog.goal_by_name[new.lower()] = node

        dialog.used_names.remove(old.lower())
        dialog.used_names.add(new.lower())

        return edit_response(f"Цель '{old}' переименована в '{new}'.")

    # --- переименование фактора ---
    if kind == "rename_factor":
        old, new = cmd[1], cmd[2]

        if old.lower() not in dialog.factor_set:
            return edit_response(f"Фактор '{old}' не найден.")

        if new.lower() in dialog.used_names:
            return edit_response("Название уже занято.")

        for r in dialog.factors_results:
            if r["factor"].lower() == old.lower():
                r["factor"] = new

        dialog.factor_set.remove(old.lower())
        dialog.factor_set.add(new.lower())

        dialog.used_names.remove(old.lower())
        dialog.used_names.add(new.lower())

        return edit_response(f"Фактор '{old}' переименован в '{new}'.")

    # --- удалить цель ---
    if kind == "delete_goal":
        name = cmd[1].lower()

        if name not in dialog.goal_by_name:
            return edit_response("Цель не найдена.")

        node = dialog.goal_by_name[name]

        # удалить из дерева
        if node.parent:
            node.parent.children.remove(node)

        # рекурсивно удалить все потомки
        def remove(n):
            dialog.used_names.discard(n.name.lower())
            dialog.goal_by_name.pop(n.name.lower(), None)
            for c in n.children:
                remove(c)

        remove(node)

        return edit_response(f"Цель '{cmd[1]}' удалена.")

    # --- удалить фактор ---
    if kind == "delete_factor":
        name = cmd[1].lower()

        if name not in dialog.factor_set:
            return edit_response("Фактор не найден.")

        dialog.factor_set.remove(name)
        dialog.used_names.discard(name)

        dialog.factors_results = [
            r for r in dialog.factors_results if r["factor"].lower() != name
        ]

        return edit_response(f"Фактор '{cmd[1]}' удалён.")

    # --- автоудаление ---
    if kind == "delete_auto":
        name = cmd[1]

        if name.lower() in dialog.goal_by_name:
            return handle_edit_command(("delete_goal", name))

        if name.lower() in dialog.factor_set:
            return handle_edit_command(("delete_factor", name))

        return edit_response("Элемент не найден.")

    # --- добавить подцель ---
    if kind == "add_subgoal":
        new, parent = cmd[1], cmd[2]

        if parent.lower() not in dialog.goal_by_name:
            return edit_response("Родительская цель не найдена.")

        if new.lower() in dialog.used_names:
            return edit_response("Название уже используется.")

        parent_node = dialog.goal_by_name[parent.lower()]

        if parent_node.level >= dialog.max_level:
            return edit_response("Нельзя добавить глубже максимального уровня.")

        child = parent_node.add_child(new)

        dialog.goal_by_name[new.lower()] = child
        dialog.used_names.add(new.lower())

        return edit_response(f"Подцель '{new}' добавлена к '{parent}'.")

    return edit_response("Неизвестная команда.")
