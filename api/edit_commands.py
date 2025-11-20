import re
from typing import Optional

from core.dialog_state import dialog
from core.schemas import DialogResponse
from models.goal import serialize_tree, collect_goals, GoalNode


# Список состояний, которые относятся к "мастерам" редактирования/добавления
EDIT_FLOW_STATES = {
    "edit_goal_wait_new_name",
    "add_goal_wait_parent",
    "add_goal_ask_use_factors",
    "add_goal_factor_confirm",
    "add_goal_factor_p",
    "add_goal_factor_q",
}


def _recalc_levels(root: GoalNode):
    """Пересчитать уровни (level) всего дерева после перемещения цели."""
    def dfs(node: GoalNode, lvl: int):
        node.level = lvl
        for ch in node.children:
            dfs(ch, lvl + 1)

    dfs(root, 1)


def _rebuild_goals_ordered():
    """Пересобрать список целей для ОСЭ после изменения дерева."""
    if dialog.root:
        dialog.goals_ordered = collect_goals(dialog.root)
    else:
        dialog.goals_ordered = []


def try_parse_edit_command(text: str):
    """
    Парсим команды редактирования (без учёта состояний мастера).
    Команды работают и с кавычками, и без, регистр не важен.
    Возвращаем tuple('тип_команды', ...), либо None.
    """
    s = text.strip()
    if not s:
        return None

    # --- интерактивное изменение цели: изменить цель X ---
    m = re.match(r'изменить\s+цель\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'изменить\s+цель\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("edit_goal_interactive", m.group(1))

    # --- одношаговое переименование цели: измени цель "A" на "B" ---
    m = re.match(r'измени\s+цель\s+"(.+?)"\s+на\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("rename_goal", m.group(1), m.group(2))

    # --- переименование фактора ---
    m = re.match(r'измени\s+фактор\s+"(.+?)"\s+на\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("rename_factor", m.group(1), m.group(2))

    # --- переместить цель X под Y ---
    m = re.match(r'перемести\s+цель\s+"(.+?)"\s+под\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'перемести\s+цель\s+(.+?)\s+под\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("move_goal", m.group(1), m.group(2))

    # --- удалить цель X ---
    m = re.match(r'удали\s+цель\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'удали\s+цель\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("delete_goal", m.group(1))

    # --- удалить фактор Y ---
    m = re.match(r'удали\s+фактор\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'удали\s+фактор\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("delete_factor", m.group(1))

    # --- универсальное удаление: удали X / удали "X" ---
    m = re.match(r'удали\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'удали\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("delete_auto", m.group(1))

    # --- старая форма добавления подцели с кавычками ---
    m = re.match(r'добавь\s+"(.+?)"\s+как\s+подцель\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_subgoal_old", m.group(1), m.group(2))

    # --- новая форма: добавь цель X как подцель Y ---
    m = re.match(r'добав(ить|ь)\s+цель\s+"(.+?)"\s+как\s+подцель\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'добав(ить|ь)\s+цель\s+(.+?)\s+как\s+подцель\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_goal_with_parent", m.group(2), m.group(3))

    # --- новая форма: добавь цель X (родителя спросим отдельно) ---
    m = re.match(r'добав(ить|ь)\s+цель\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'добав(ить|ь)\s+цель\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_goal_no_parent", m.group(2))

    # --- добавить фактор (в любой момент, в т.ч. после завершения) ---
    m = re.match(r'добав(ить|ь)\s+фактор\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_factor_after_finish", m.group(2))

    m = re.match(r'фактор\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_factor_after_finish", m.group(1))

    m = re.match(r'добав(ить|ь)\s+"(.+?)"\s+как\s+фактор\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_factor_after_finish", m.group(2))

    # --- пропустить / продолжить ---
    if s.lower() in ["пропустить", "продолжить"]:
        return ("skip",)

    # --- завершить ОСЭ ---
    if s.lower() in ["завершить", "конец", "finish", "stop"]:
        return ("finish",)

    return None


def edit_response(msg: str) -> DialogResponse:
    """
    Унифицированный ответ после команды (НЕ мастера),
    + подсказка по доступным командам.
    """
    help_text = (
        msg + "\n\n"
        "Доступные команды:\n"
        "- изменить цель X\n"
        "- измени цель \"A\" на \"B\"\n"
        "- перемести цель X под Y\n"
        "- удали цель X\n"
        "- удали фактор Y\n"
        "- добавь цель X как подцель Y\n"
        "- добавь цель X (родителя спросят отдельно)\n"
        "- добавь фактор \"F\" (оценка для всех целей)\n"
        "- пропустить / продолжить\n"
        "- завершить\n"
    )

    return DialogResponse(
        phase=dialog.phase,
        state=dialog.state,
        question=help_text,
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
        message=msg,
    )


# =====================================================================
#  ОБРАБОТЧИКИ КОМАНД (не зависят от состояний мастера)
# =====================================================================

def handle_edit_command(cmd) -> DialogResponse:
    kind = cmd[0]

    # --- пропустить шаг ---
    if kind == "skip":
        return edit_response("Шаг пропущен.")

    # --- завершить ОСЭ ---
    if kind == "finish":
        dialog.state = "finish_ose"
        return edit_response("Диалог ОСЭ завершён. Можно добавить новый фактор или редактировать цели.")

    # --- интерактивное изменение цели: изменить цель X ---
    if kind == "edit_goal_interactive":
        name = cmd[1].strip()
        key = name.lower()

        if key not in dialog.goal_by_name:
            return edit_response(f"Цель '{name}' не найдена.")

        dialog.edit_goal_target = dialog.goal_by_name[key]
        dialog.prev_state = dialog.state
        dialog.state = "edit_goal_wait_new_name"

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=f"Введите новое имя для цели '{dialog.edit_goal_target.name}':",
            tree=serialize_tree(dialog.root) if dialog.root else [],
            ose_results=dialog.factors_results,
            message=f"Изменяем цель '{dialog.edit_goal_target.name}'.",
        )

    # --- одношаговое переименование цели: измени цель "A" на "B" ---
    if kind == "rename_goal":
        old, new = cmd[1].strip(), cmd[2].strip()
        old_l = old.lower()
        new_l = new.lower()

        if old_l not in dialog.goal_by_name:
            return edit_response(f"Цель '{old}' не найдена.")

        if new_l in dialog.used_names:
            return edit_response("Новое название уже используется.")

        node = dialog.goal_by_name.pop(old_l)
        old_display = node.name

        node.name = new
        dialog.goal_by_name[new_l] = node
        dialog.used_names.remove(old_l)
        dialog.used_names.add(new_l)

        # обновляем имя в результатах ОСЭ
        for r in dialog.factors_results:
            if r["goal"] == old_display:
                r["goal"] = new

        return edit_response(f"Цель '{old_display}' переименована в '{new}'.")

    # --- переименование фактора ---
    if kind == "rename_factor":
        old, new = cmd[1].strip(), cmd[2].strip()
        old_l = old.lower()
        new_l = new.lower()

        if old_l not in dialog.factor_set:
            return edit_response(f"Фактор '{old}' не найден.")

        if new_l in dialog.used_names:
            return edit_response("Новое название уже используется.")

        for r in dialog.factors_results:
            if r["factor"].lower() == old_l:
                r["factor"] = new

        dialog.factor_set.remove(old_l)
        dialog.factor_set.add(new_l)
        dialog.used_names.remove(old_l)
        dialog.used_names.add(new_l)

        return edit_response(f"Фактор '{old}' переименован в '{new}'.")

    # --- переместить цель X под Y ---
    if kind == "move_goal":
        name, parent = cmd[1].strip(), cmd[2].strip()
        name_l, parent_l = name.lower(), parent.lower()

        if not dialog.root:
            return edit_response("Дерево целей ещё не построено.")

        if name_l not in dialog.goal_by_name:
            return edit_response(f"Цель '{name}' не найдена.")

        if parent_l not in dialog.goal_by_name:
            return edit_response(f"Цель-родитель '{parent}' не найдена.")

        node = dialog.goal_by_name[name_l]
        new_parent = dialog.goal_by_name[parent_l]

        # запретим двигать корень
        if node is dialog.root:
            return edit_response("Нельзя переместить корневую цель.")

        # запретим делать ребёнка родителем самого себя (и своих потомков)
        cur = new_parent
        while cur is not None:
            if cur is node:
                return edit_response("Нельзя переместить цель под одну из её подцелей.")
            cur = cur.parent

        # проверка глубины
        if new_parent.level >= dialog.max_level:
            return edit_response(
                f"Нельзя переместить под '{new_parent.name}': глубина превысит максимум ({dialog.max_level})."
            )

        # удаляем из старого родителя
        if node.parent:
            node.parent.children.remove(node)

        # новый родитель
        node.parent = new_parent
        new_parent.children.append(node)

        # пересчитываем уровни
        _recalc_levels(dialog.root)
        _rebuild_goals_ordered()

        return edit_response(f"Цель '{node.name}' перемещена под '{new_parent.name}'.")

    # --- удалить цель ---
    if kind == "delete_goal":
        name = cmd[1].strip()
        name_l = name.lower()

        if name_l not in dialog.goal_by_name:
            return edit_response(f"Цель '{name}' не найдена.")

        node = dialog.goal_by_name[name_l]

        # не даём удалить корень "тихо" — можно, но допустим разрешим
        if node.parent:
            node.parent.children.remove(node)
        else:
            # удаляем всё дерево
            dialog.root = None

        removed_names = []

        def remove_subtree(n: GoalNode):
            removed_names.append(n.name)
            dialog.goal_by_name.pop(n.name.lower(), None)
            dialog.used_names.discard(n.name.lower())
            for ch in n.children:
                remove_subtree(ch)

        remove_subtree(node)

        # чистим ОСЭ
        dialog.factors_results = [
            r for r in dialog.factors_results if r["goal"] not in removed_names
        ]

        if dialog.root:
            _rebuild_goals_ordered()
        else:
            dialog.goals_ordered = []

        return edit_response(f"Цель '{name}' и её подцели удалены.")

    # --- удалить фактор ---
    if kind == "delete_factor":
        name = cmd[1].strip()
        name_l = name.lower()

        if name_l not in dialog.factor_set:
            return edit_response(f"Фактор '{name}' не найден.")

        dialog.factor_set.remove(name_l)
        dialog.used_names.discard(name_l)

        dialog.factors_results = [
            r for r in dialog.factors_results if r["factor"].lower() != name_l
        ]

        return edit_response(f"Фактор '{name}' удалён.")

    # --- автоудаление: сначала пробуем цель, потом фактор ---
    if kind == "delete_auto":
        name = cmd[1].strip()
        name_l = name.lower()

        if name_l in dialog.goal_by_name:
            return handle_edit_command(("delete_goal", name))
        if name_l in dialog.factor_set:
            return handle_edit_command(("delete_factor", name))

        return edit_response(f"'{name}' не найдено ни среди целей, ни среди факторов.")

    # --- старая add_subgoal (с кавычками) ---
    if kind == "add_subgoal_old":
        new, parent = cmd[1].strip(), cmd[2].strip()
        new_l, parent_l = new.lower(), parent.lower()

        if parent_l not in dialog.goal_by_name:
            return edit_response(f"Родительская цель '{parent}' не найдена.")

        if new_l in dialog.used_names:
            return edit_response("Такое название уже используется.")

        parent_node = dialog.goal_by_name[parent_l]
        if parent_node.level >= dialog.max_level:
            return edit_response("Нельзя добавить глубже максимального уровня дерева.")

        child = parent_node.add_child(new)
        dialog.goal_by_name[new_l] = child
        dialog.used_names.add(new_l)
        _recalc_levels(dialog.root)
        _rebuild_goals_ordered()

        return edit_response(f"Подцель '{new}' добавлена к цели '{parent}'.")

    # --- добавь цель X как подцель Y ---
    if kind == "add_goal_with_parent":
        new, parent = cmd[1].strip(), cmd[2].strip()
        new_l, parent_l = new.lower(), parent.lower()

        if not dialog.root:
            return edit_response("Дерево целей ещё не построено. Сначала задайте главную цель.")

        if parent_l not in dialog.goal_by_name:
            return edit_response(f"Родительская цель '{parent}' не найдена.")

        if new_l in dialog.used_names:
            return edit_response("Такое название уже используется.")

        parent_node = dialog.goal_by_name[parent_l]
        if parent_node.level >= dialog.max_level:
            return edit_response("Нельзя добавить глубже максимального уровня дерева.")

        child = parent_node.add_child(new)
        dialog.goal_by_name[new_l] = child
        dialog.used_names.add(new_l)
        _recalc_levels(dialog.root)
        _rebuild_goals_ordered()

        dialog.add_goal_current_goal = child
        dialog.add_goal_name = child.name

        # если факторов ещё нет — просто добавляем цель
        if not dialog.factor_set:
            return edit_response(
                f"Цель '{child.name}' добавлена как подцель '{parent_node.name}'.\n"
                f"Факторы пока не заданы. Вы можете добавить их позже с помощью команды 'добавить фактор'."
            )

        # запускаем мастер ввода p/q по уже существующим факторам
        dialog.prev_state = dialog.state
        dialog.state = "add_goal_ask_use_factors"

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=(
                f"Цель '{child.name}' добавлена как подцель '{parent_node.name}'.\n"
                "Хотите ввести значения факторов для этой цели? (да/нет)"
            ),
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
            message=f"Добавлена новая цель '{child.name}'.",
        )

    # --- добавь цель X (родителя спросим отдельно) ---
    if kind == "add_goal_no_parent":
        new = cmd[1].strip()
        new_l = new.lower()

        if not dialog.root:
            return edit_response("Дерево целей ещё не построено. Сначала задайте главную цель.")

        if new_l in dialog.used_names:
            return edit_response("Такое название уже используется.")

        dialog.add_goal_name = new
        dialog.prev_state = dialog.state
        dialog.state = "add_goal_wait_parent"

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=f"Укажите родительскую цель для '{new}':",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
            message=f"Добавление цели '{new}'.",
        )

    # --- добавить фактор 'после завершения' (для всех целей) ---
    if kind == "add_factor_after_finish":
        fname = cmd[1].strip()
        fl = fname.lower()

        if not dialog.root:
            return edit_response("Дерево целей ещё не построено. Сначала задайте цели.")

        if fl in dialog.used_names:
            return edit_response(f"Название '{fname}' уже используется.")

        dialog.used_names.add(fl)
        dialog.factor_set.add(fl)
        dialog.current_factor_name = fname

        if not dialog.goals_ordered:
            _rebuild_goals_ordered()
        if not dialog.goals_ordered:
            return edit_response("Список целей пуст, добавлять фактор некуда.")

        dialog.phase = "adpose"
        dialog.state = "ask_p"
        dialog.current_goal_idx = 0

        first_goal = dialog.goals_ordered[0]

        return DialogResponse(
            phase="adpose",
            state="ask_p",
            question=(
                f"Добавляем новый фактор '{fname}'.\n"
                f"Введите p (0..1) для цели '{first_goal.name}':"
            ),
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
            message=f"Фактор '{fname}' добавлен. Начинаем оценку для всех целей.",
        )

    # неизвестная команда
    return edit_response("Команда не распознана.")
def handle_edit_flow(ans: str) -> DialogResponse:
    """
    Обработка шагов "мастеров" редактирования/добавления,
    которые занимают несколько сообщений.
    """
    text = ans.strip()

    # --------------------------------------------------------
    # 1) Мастер: изменить цель X → новое имя
    # --------------------------------------------------------
    if dialog.state == "edit_goal_wait_new_name":
        if not dialog.edit_goal_target:
            # что-то пошло не так, выходим
            dialog.state = dialog.prev_state or dialog.state
            dialog.prev_state = None
            return edit_response("Ошибка: цель для редактирования не найдена.")

        new_name = text
        if not new_name:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="Имя не может быть пустым. Введите новое имя цели:",
                tree=serialize_tree(dialog.root) if dialog.root else [],
                ose_results=dialog.factors_results,
            )

        old_display = dialog.edit_goal_target.name
        old_l = old_display.lower()
        new_l = new_name.lower()

        if new_l != old_l and new_l in dialog.used_names:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="Такое имя уже используется. Введите другое имя:",
                tree=serialize_tree(dialog.root) if dialog.root else [],
                ose_results=dialog.factors_results,
            )

        # переименование
        dialog.goal_by_name.pop(old_l, None)
        dialog.used_names.discard(old_l)

        dialog.edit_goal_target.name = new_name

        dialog.goal_by_name[new_l] = dialog.edit_goal_target
        dialog.used_names.add(new_l)

        # обновим результаты ОСЭ
        for r in dialog.factors_results:
            if r["goal"] == old_display:
                r["goal"] = new_name

        # завершаем мастер, возвращаемся в прежнее состояние
        dialog.state = dialog.prev_state or dialog.state
        dialog.prev_state = None
        dialog.edit_goal_target = None

        msg = (
            f"Имя цели '{old_display}' изменено на '{new_name}'.\n\n"
            "Для изменения факторов этой цели вы можете использовать команды:\n"
            "- добавь фактор \"F\" (оценка для всех целей)\n"
            "- удали фактор F\n"
            "- или запусти ОСЭ заново для новых факторов."
        )

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=msg,
            tree=serialize_tree(dialog.root) if dialog.root else [],
            ose_results=dialog.factors_results,
            message=f"Цель переименована в '{new_name}'.",
        )

    # --------------------------------------------------------
    # 2) Мастер: добавь цель X → спросить родителя
    # --------------------------------------------------------
    if dialog.state == "add_goal_wait_parent":
        parent_name = text
        parent_l = parent_name.lower()

        if not dialog.add_goal_name:
            # что-то пошло не так
            dialog.state = dialog.prev_state or dialog.state
            dialog.prev_state = None
            return edit_response("Ошибка: не запомнили имя новой цели.")

        if not dialog.root:
            return edit_response("Дерево целей ещё не построено.")

        if parent_l not in dialog.goal_by_name:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question=f"Родительская цель '{parent_name}' не найдена. Укажите существующую цель:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        parent_node = dialog.goal_by_name[parent_l]
        if parent_node.level >= dialog.max_level:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question=(
                    f"Цель '{parent_node.name}' уже на максимальной глубине. "
                    f"Укажите другую родительскую цель:"
                ),
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        new_name = dialog.add_goal_name
        new_l = new_name.lower()

        if new_l in dialog.used_names:
            dialog.state = dialog.prev_state or dialog.state
            dialog.prev_state = None
            dialog.add_goal_name = None
            return edit_response("Такое имя уже используется.")

        child = parent_node.add_child(new_name)
        dialog.goal_by_name[new_l] = child
        dialog.used_names.add(new_l)
        _recalc_levels(dialog.root)
        _rebuild_goals_ordered()

        dialog.add_goal_current_goal = child

        # если факторов нет — просто выходим
        if not dialog.factor_set:
            dialog.state = dialog.prev_state or dialog.state
            dialog.prev_state = None
            dialog.add_goal_name = None
            return edit_response(
                f"Цель '{child.name}' добавлена как подцель '{parent_node.name}'.\n"
                "Факторы пока не заданы."
            )

        dialog.state = "add_goal_ask_use_factors"

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=(
                f"Цель '{child.name}' добавлена как подцель '{parent_node.name}'.\n"
                "Хотите ввести значения факторов для этой цели? (да/нет)"
            ),
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
            message=f"Добавлена новая цель '{child.name}'.",
        )

    # --------------------------------------------------------
    # 3) Мастер: добавленная цель → спросить, вводить ли факторы
    # --------------------------------------------------------
    if dialog.state == "add_goal_ask_use_factors":
        if not dialog.add_goal_current_goal:
            dialog.state = dialog.prev_state or dialog.state
            dialog.prev_state = None
            return edit_response("Ошибка: цель для ввода факторов не найдена.")

        if text.lower().startswith("д"):  # да
            # собираем список факторов в виде отображаемых имён
            factors_map: dict[str, str] = {}
            for r in dialog.factors_results:
                fl = r["factor"].lower()
                factors_map[fl] = r["factor"]
            # на случай, если фактор_set есть, а результатов ещё нет
            for fl in dialog.factor_set:
                if fl not in factors_map:
                    factors_map[fl] = fl

            dialog.add_goal_factors_list = list(factors_map.values())
            dialog.add_goal_factor_index = 0

            if not dialog.add_goal_factors_list:
                # факторов нет, выходим
                dialog.state = dialog.prev_state or dialog.state
                dialog.prev_state = None
                return edit_response("Факторы отсутствуют, вводить нечего.")

            dialog.state = "add_goal_factor_confirm"
            return _ask_next_factor_confirm()

        # нет — выходим из мастера
        dialog.state = dialog.prev_state or dialog.state
        dialog.prev_state = None
        dialog.add_goal_name = None
        dialog.add_goal_current_goal = None
        dialog.add_goal_factors_list = []
        dialog.add_goal_factor_index = 0
        dialog.add_goal_current_factor = None
        dialog.add_goal_tmp_p = None

        return edit_response("Цель добавлена без ввода значений факторов.")

    # --------------------------------------------------------
    # 4) Мастер: "Хотите ввести значения для фактора F?" (да/нет)
    # --------------------------------------------------------
    if dialog.state == "add_goal_factor_confirm":
        if not dialog.add_goal_current_goal:
            dialog.state = dialog.prev_state or dialog.state
            dialog.prev_state = None
            return edit_response("Ошибка: нет текущей цели.")

        if text.lower().startswith("д"):  # да
            # переходим к вводу p
            dialog.state = "add_goal_factor_p"
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question=(
                    f"Введите p (0..1) для фактора '{dialog.add_goal_current_factor}' "
                    f"и цели '{dialog.add_goal_current_goal.name}':"
                ),
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        # нет — следующий фактор
        dialog.add_goal_factor_index += 1
        return _ask_next_factor_confirm()

    # --------------------------------------------------------
    # 5) Мастер: ввод p для фактора
    # --------------------------------------------------------
    if dialog.state == "add_goal_factor_p":
        try:
            p = float(text)
        except ValueError:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="Некорректный ввод. Введите p (число от 0 до 1):",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if p < 0 or p > 1:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="p должно быть числом от 0 до 1. Введите p ещё раз:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if p == 1:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="p не может быть равно 1. Введите значение меньше 1:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        dialog.add_goal_tmp_p = p
        dialog.state = "add_goal_factor_q"

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=(
                f"Введите q (0..1) для фактора '{dialog.add_goal_current_factor}' "
                f"и цели '{dialog.add_goal_current_goal.name}':"
            ),
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    # --------------------------------------------------------
    # 6) Мастер: ввод q для фактора
    # --------------------------------------------------------
    if dialog.state == "add_goal_factor_q":
        import math

        try:
            q = float(text)
        except ValueError:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="Некорректный ввод. Введите q (число от 0 до 1):",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if q < 0 or q > 1:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="q должно быть от 0 до 1. Введите q ещё раз:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if q == 0:
            return DialogResponse(
                phase=dialog.phase,
                state=dialog.state,
                question="q = 0 означает отсутствие влияния. Введите q > 0:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        p = dialog.add_goal_tmp_p or 0.0
        if p <= 0:
            H = 0.0
        else:
            try:
                H = -q * math.log(1 - p)
            except ValueError:
                H = 0.0

        dialog.factors_results.append({
            "goal": dialog.add_goal_current_goal.name,
            "factor": dialog.add_goal_current_factor,
            "H": round(H, 4),
        })

        # следующий фактор
        dialog.add_goal_factor_index += 1
        dialog.add_goal_tmp_p = None
        dialog.state = "add_goal_factor_confirm"

        return _ask_next_factor_confirm()

    # если состояние не распознано — отдадим общее сообщение
    return edit_response("Неизвестное состояние мастера редактирования.")


def _ask_next_factor_confirm() -> DialogResponse:
    """Шаг мастера: спросить, хотим ли вводить значения для следующего фактора."""
    if dialog.add_goal_factor_index >= len(dialog.add_goal_factors_list):
        # факторы закончились — выходим из мастера
        goal_name = dialog.add_goal_current_goal.name if dialog.add_goal_current_goal else "цели"

        dialog.state = dialog.prev_state or dialog.state
        dialog.prev_state = None
        dialog.add_goal_name = None
        dialog.add_goal_current_goal = None
        dialog.add_goal_factors_list = []
        dialog.add_goal_factor_index = 0
        dialog.add_goal_current_factor = None
        dialog.add_goal_tmp_p = None

        return edit_response(f"Ввод значений факторов для {goal_name} завершён.")

    factor_name = dialog.add_goal_factors_list[dialog.add_goal_factor_index]
    dialog.add_goal_current_factor = factor_name
    dialog.state = "add_goal_factor_confirm"

    return DialogResponse(
        phase=dialog.phase,
        state=dialog.state,
        question=(
            f"Хотите ввести значения для фактора '{factor_name}' "
            f"для цели '{dialog.add_goal_current_goal.name}'? (да/нет)"
        ),
        tree=serialize_tree(dialog.root),
        ose_results=dialog.factors_results,
    )
