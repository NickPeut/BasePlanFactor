from core.dialog_state import dialog
from core.schemas import DialogResponse

from db.goal import GoalNode, serialize_tree, collect_goals
from db.session import SessionLocal
from db.goals import (
    get_classifier_with_items,
    create_classifier,
    add_classifier_item,
    replace_goals_from_tree,
)


def _persist_tree():
    scheme_id = getattr(dialog, "active_scheme_id", None)
    if scheme_id is None:
        return
    session = SessionLocal()
    try:
        replace_goals_from_tree(session, scheme_id, dialog.root)
    finally:
        session.close()


def _resp(state: str, question: str) -> DialogResponse:
    return DialogResponse(
        phase="adpacf",
        state=state,
        question=question,
        tree=serialize_tree(dialog.root) if dialog.root else [],
    )


def _resp_phase(phase: str, state: str, question: str) -> DialogResponse:
    return DialogResponse(
        phase=phase,
        state=state,
        question=question,
        tree=serialize_tree(dialog.root) if dialog.root else [],
    )


def _init_classifiers() -> DialogResponse:
    dialog.state = "clf_name"
    dialog.clfs = []
    dialog.clf_tmp_name = None
    dialog.clf_parent_goal = None
    dialog.clf_indices = None
    dialog.clf_level = 1
    return _resp("clf_name", "Введите название классификатора (признака структуризации).")


def _start_adpose() -> DialogResponse:
    dialog.phase = "adpose"
    dialog.state = "ask_factor_name"
    dialog.goals_ordered = collect_goals(dialog.root)
    return _resp_phase("adpose", "ask_factor_name", "Введите название фактора:")


def _find_goal(raw: str):
    raw = raw.strip()
    if raw.isdigit():
        target_id = int(raw)

        def _find_by_id(n: GoalNode):
            if not n:
                return None
            if getattr(n, "id", None) == target_id:
                return n
            for ch in getattr(n, "children", []) or []:
                got = _find_by_id(ch)
                if got:
                    return got
            return None

        return _find_by_id(dialog.root)

    return dialog.goal_by_name.get(raw.lower())


def _clf_combo_text():
    parts = []
    for i, clf in enumerate(dialog.clfs):
        idx = dialog.clf_indices[i]
        parts.append(clf["items"][idx])
    return parts


def _clf_advance():
    for i in range(len(dialog.clf_indices) - 1, -1, -1):
        dialog.clf_indices[i] += 1
        if dialog.clf_indices[i] < len(dialog.clfs[i]["items"]):
            return True
        dialog.clf_indices[i] = 0
    return False


def _handle_ask_root(text: str) -> DialogResponse:
    if not text:
        return DialogResponse(phase="adpacf", state="ask_root", question="Введите название главной цели:", tree=[])

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
    _persist_tree()

    return DialogResponse(
        phase="adpacf",
        state="ask_add_subgoal",
        question=(
            f"Добавить подцель для '{root.name}'? (да/нет)\n"
            "Если дерево укрупнено достаточно — ответь 'нет' и перейдём к классификаторам."
        ),
        tree=serialize_tree(root),
    )


def _handle_ask_add_subgoal(text: str) -> DialogResponse:
    answer_low = text.lower()

    if answer_low == "да":
        if dialog.current_node.level >= dialog.max_level:
            return _resp(
                "ask_add_subgoal",
                (
                    f"Достигнут максимальный уровень ({dialog.max_level}). "
                    f"Подцель для '{dialog.current_node.name}' добавить нельзя. "
                    "Ответьте 'нет', чтобы вернуться к родительской цели."
                ),
            )
        dialog.state = "ask_subgoal_name"
        return _resp("ask_subgoal_name", f"Введите название подцели для '{dialog.current_node.name}':")

    if dialog.current_node.parent:
        dialog.current_node = dialog.current_node.parent
        return _resp("ask_add_subgoal", f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)")

    if not getattr(dialog, "clf_done", False):
        return _init_classifiers()

    return _start_adpose()


def _handle_ask_subgoal_name(text: str) -> DialogResponse:
    if not text:
        return _resp("ask_subgoal_name", "Название не может быть пустым. Введите подцель:")

    if text.lower() in dialog.used_names:
        return _resp("ask_subgoal_name", "Название уже используется. Введите другое название подцели:")

    child = dialog.current_node.add_child(text)
    dialog.current_node = child
    dialog.used_names.add(text.lower())
    dialog.goal_by_name[text.lower()] = child
    dialog.state = "ask_add_subgoal"
    _persist_tree()

    return _resp("ask_add_subgoal", f"Добавить подцель для '{child.name}'? (да/нет)")


def _handle_clf_name(text: str) -> DialogResponse:
    if not text:
        return _resp("clf_name", "Введите название классификатора:")

    dialog.clf_tmp_name = text
    dialog.state = "clf_items"
    return _resp("clf_items", f"Классификатор = '{dialog.clf_tmp_name}'.\nВведите элементы через запятую (ключевые слова):")


def _handle_clf_items(text: str) -> DialogResponse:
    items = [x.strip() for x in text.split(",") if x.strip()]
    if not items:
        return _resp("clf_items", "Введите хотя бы один элемент через запятую:")

    scheme_id = getattr(dialog, "active_scheme_id", None)
    session = SessionLocal()
    try:
        clf = get_classifier_with_items(session, scheme_id, dialog.clf_tmp_name, level=dialog.clf_level)
        if not clf:
            clf = create_classifier(session, scheme_id, dialog.clf_tmp_name, level=dialog.clf_level)

        existing = {it.value.strip().lower() for it in (clf.items or []) if it.value}
        for v in items:
            v_norm = v.strip()
            if not v_norm:
                continue
            if v_norm.lower() in existing:
                continue
            try:
                add_classifier_item(session, clf.id, v_norm)
                existing.add(v_norm.lower())
            except Exception:
                session.rollback()

        clf = get_classifier_with_items(session, scheme_id, dialog.clf_tmp_name, level=dialog.clf_level)
        all_items = [it.value for it in (clf.items or [])]
    finally:
        session.close()

    dialog.clfs.append({"name": dialog.clf_tmp_name, "items": all_items, "level": dialog.clf_level})
    dialog.clf_tmp_name = None
    dialog.state = "clf_more"

    r = 1
    for c in dialog.clfs:
        r *= max(1, len(c["items"]))

    return _resp("clf_more", f"Классификатор добавлен. Текущее число сочетаний R = {r}.\nДобавить ещё классификатор? (да/нет)")


def _handle_clf_more(text: str) -> DialogResponse:
    a = text.lower()
    if a == "да":
        dialog.clf_level += 1
        dialog.state = "clf_name"
        return _resp("clf_name", "Введите название следующего классификатора:")

    if len(dialog.clfs) < 2:
        dialog.state = "clf_name"
        return _resp("clf_name", "Нужно минимум 2 классификатора. Введите название следующего:")

    dialog.state = "clf_parent_goal"
    return _resp("clf_parent_goal", "Введите название цели-родителя для структуризации:")


def _handle_clf_parent_goal(text: str) -> DialogResponse:
    parent = _find_goal(text)
    if parent is None:
        return _resp("clf_parent_goal", "Цель не найдена. Введите название цели точно как в дереве:")

    dialog.clf_parent_goal = parent
    dialog.clf_indices = [0 for _ in dialog.clfs]
    dialog.state = "clf_combo_decide"

    combo_s = " / ".join(_clf_combo_text())
    return _resp("clf_combo_decide", f"Сочетание ⟨{combo_s}⟩ включить как подцель? (да/нет)")


def _handle_clf_combo_decide(text: str) -> DialogResponse:
    answer_low = text.lower()
    if answer_low not in ("да", "нет"):
        combo_s = " / ".join(_clf_combo_text())
        return _resp("clf_combo_decide", f"Сочетание ⟨{combo_s}⟩ включить как подцель? (да/нет)")

    parent = dialog.clf_parent_goal
    if parent:
        name = " / ".join(_clf_combo_text())
        if answer_low == "да":
            if parent.level < dialog.max_level and name.lower() not in dialog.used_names:
                child = parent.add_child(name)
                dialog.used_names.add(name.lower())
                dialog.goal_by_name[name.lower()] = child
                _persist_tree()

    has_next = _clf_advance()
    if not has_next:
        dialog.clf_done = True
        dialog.clf_parent_goal = None
        dialog.clf_indices = None
        dialog.phase = "adpose"
        dialog.state = "ask_factor_name"
        return _resp(
            "ask_factor_name",
            "Введите название фактора:",
        )

    combo_s = " / ".join(_clf_combo_text())
    return _resp("clf_combo_decide", f"Сочетание ⟨{combo_s}⟩ включить как подцель? (да/нет)")

_HANDLERS = {
    "ask_root": _handle_ask_root,
    "ask_add_subgoal": _handle_ask_add_subgoal,
    "ask_subgoal_name": _handle_ask_subgoal_name,
    "clf_name": _handle_clf_name,
    "clf_items": _handle_clf_items,
    "clf_more": _handle_clf_more,
    "clf_parent_goal": _handle_clf_parent_goal,
    "clf_combo_decide": _handle_clf_combo_decide,
}


def handle_adpacf(ans: str) -> DialogResponse:
    text = ans.strip()

    handler = _HANDLERS.get(dialog.state)
    if not handler:
        return DialogResponse(
            phase="adpacf",
            state="error",
            question="Неизвестное состояние в АДПАЦФ.",
            tree=serialize_tree(dialog.root) if dialog.root else [],
        )

    return handler(text)
