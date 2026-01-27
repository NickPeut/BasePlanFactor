import re

from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import GoalNode, collect_goals, serialize_tree
from db.session import SessionLocal
from db.goals import (
    list_classifiers,
    create_classifier,
    add_classifier_item,
    get_classifier_with_items,
)


def edit_response(text):
    return DialogResponse(
        phase=dialog.phase,
        state=dialog.state,
        question=text,
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
        message=None,
    )


def try_parse_edit_command(text):
    s = text.strip()

    m = re.match(r'добав(ить|ь)\s+классификатор\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'добав(ить|ь)\s+классификатор\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("add_classifier", m.group(2))

    m = re.match(
        r'добав(ить|ь)\s+элемент\s+"(.+?)"\s+в\s+классификатор\s+"(.+?)"\s*$',
        s,
        flags=re.IGNORECASE,
    )
    if not m:
        m = re.match(
            r'добав(ить|ь)\s+элемент\s+(.+?)\s+в\s+классификатор\s+(.+?)\s*$',
            s,
            flags=re.IGNORECASE,
        )
    if m:
        return ("add_classifier_item", m.group(2), m.group(3))

    if s.lower() in ["покажи классификаторы", "показать классификаторы", "классификаторы"]:
        return ("show_classifiers",)

    m = re.match(
        r'начать\s+классификаторы\s+для\s+цели\s+"(.+?)"\s*$',
        s,
        flags=re.IGNORECASE,
    )
    if not m:
        m = re.match(
            r'начать\s+классификаторы\s+для\s+цели\s+(.+?)\s*$',
            s,
            flags=re.IGNORECASE,
        )
    if m:
        return ("clf_start_for_goal", m.group(1))

    m = re.match(
        r'используй\s+классификаторы\s+"(.+?)"\s+и\s+"(.+?)"\s*$',
        s,
        flags=re.IGNORECASE,
    )
    if not m:
        m = re.match(
            r'используй\s+классификаторы\s+(.+?)\s+и\s+(.+?)\s*$',
            s,
            flags=re.IGNORECASE,
        )
    if m:
        return ("clf_use_two", m.group(1), m.group(2))

    if s.lower() in ["следующее сочетание", "следующее", "пропустить", "продолжить"]:
        return ("clf_next_pair",)

    if s.lower() in ["стоп классификаторы", "остановить классификаторы"]:
        return ("clf_stop",)

    return None


def cmd_show_classifiers(_cmd):
    scheme_id = dialog.active_scheme_id
    if scheme_id is None:
        return edit_response("Активная схема не выбрана.")

    session = SessionLocal()
    try:
        items = list_classifiers(session, scheme_id)
    finally:
        session.close()

    if not items:
        return edit_response("Классификаторы не заданы.")

    lines = ["Классификаторы:"]
    for c in items:
        lines.append(f"- [{c.level}] {c.name}")
    return edit_response("\n".join(lines))


def cmd_add_classifier(cmd):
    name = cmd[1].strip()
    scheme_id = dialog.active_scheme_id
    if scheme_id is None:
        return edit_response("Активная схема не выбрана.")

    level = dialog.clf_level or 1

    session = SessionLocal()
    try:
        c = create_classifier(session, scheme_id, name, level)
    except Exception:
        session.rollback()
        return edit_response("Не удалось создать классификатор.")
    finally:
        session.close()

    return edit_response(f"Классификатор '{c.name}' создан.")


def cmd_add_classifier_item(cmd):
    value = cmd[1].strip()
    clf_name = cmd[2].strip()
    scheme_id = dialog.active_scheme_id
    level = dialog.clf_level or 1

    session = SessionLocal()
    try:
        clf = get_classifier_with_items(session, scheme_id, clf_name, level)
        if not clf:
            return edit_response("Классификатор не найден.")
        add_classifier_item(session, clf.id, value)
    except Exception:
        session.rollback()
        return edit_response("Не удалось добавить элемент.")
    finally:
        session.close()

    return edit_response(f"Элемент '{value}' добавлен.")


def cmd_clf_start_for_goal(cmd):
    goal_name = cmd[1].strip().lower()

    if goal_name not in dialog.goal_by_name:
        return edit_response("Цель не найдена.")

    parent = dialog.goal_by_name[goal_name]
    if parent.level >= dialog.max_level:
        return edit_response("Достигнут максимальный уровень.")

    dialog.clf_parent_goal = parent
    dialog.clf_level = parent.level + 1
    dialog.clf_pairs = []
    dialog.clf_pair_idx = 0
    dialog.state = "ask_add_subgoal"

    return edit_response(f"Режим классификаторов для цели '{parent.name}'.")


def cmd_clf_use_two(cmd):
    c1_name, c2_name = cmd[1].strip(), cmd[2].strip()
    scheme_id = dialog.active_scheme_id
    level = dialog.clf_level

    session = SessionLocal()
    try:
        c1 = get_classifier_with_items(session, scheme_id, c1_name, level)
        c2 = get_classifier_with_items(session, scheme_id, c2_name, level)
    finally:
        session.close()

    if not c1 or not c2:
        return edit_response("Один из классификаторов не найден.")

    dialog.clf_pairs = [(a.value, b.value) for a in c1.items for b in c2.items]
    dialog.clf_pair_idx = 0
    dialog.state = "clf_pair_decide"

    x, y = dialog.clf_pairs[0]
    return DialogResponse(
        phase=dialog.phase,
        state=dialog.state,
        question=f"{x} / {y} — добавить как подцель? (да/нет)",
        tree=serialize_tree(dialog.root),
        ose_results=dialog.factors_results,
        message=None,
    )


def cmd_clf_next_pair(_cmd):
    dialog.clf_pair_idx += 1
    if dialog.clf_pair_idx >= len(dialog.clf_pairs):
        dialog.state = "ask_add_subgoal"
        dialog.clf_pairs = []
        return edit_response("Сочетания закончились.")

    x, y = dialog.clf_pairs[dialog.clf_pair_idx]
    return DialogResponse(
        phase=dialog.phase,
        state="clf_pair_decide",
        question=f"{x} / {y} — добавить? (да/нет)",
        tree=serialize_tree(dialog.root),
        ose_results=dialog.factors_results,
        message=None,
    )


def cmd_clf_stop(_cmd):
    dialog.clf_pairs = []
    dialog.clf_parent_goal = None
    dialog.state = "ask_add_subgoal"
    return edit_response("Режим классификаторов остановлен.")


_COMMANDS = {
    "show_classifiers": cmd_show_classifiers,
    "add_classifier": cmd_add_classifier,
    "add_classifier_item": cmd_add_classifier_item,
    "clf_start_for_goal": cmd_clf_start_for_goal,
    "clf_use_two": cmd_clf_use_two,
    "clf_next_pair": cmd_clf_next_pair,
    "clf_stop": cmd_clf_stop,
}


def handle_edit_command(cmd):
    kind = cmd[0]
    handler = _COMMANDS.get(kind)
    if not handler:
        return edit_response("Неизвестная команда.")
    return handler(cmd)
