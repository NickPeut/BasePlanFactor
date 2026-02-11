import re

from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import collect_goals, serialize_tree
from db.session import SessionLocal
from db.goals import (
    list_classifiers,
    add_classifier_item,
    get_classifier_with_items,
    delete_classifier,
    replace_goals_from_tree, replace_ose_results,
)

from api.adpose import _strip_summaries, _append_goal_summaries


def edit_response(text):
    return DialogResponse(
        phase=dialog.phase,
        state=dialog.state,
        question=text,
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
        message=None,
    )

def _rebuild_goal_maps():
    dialog.used_names = set()
    dialog.goal_by_name = {}
    if not dialog.root:
        return
    for g in collect_goals(dialog.root):
        dialog.used_names.add(g.name.lower())
        dialog.goal_by_name[g.name.lower()] = g


def _recalc_ose_results():
    base = _strip_summaries(dialog.factors_results)
    dialog.factors_results = _append_goal_summaries(base, dialog.root) if dialog.root else base



def _persist_tree():
    scheme_id = getattr(dialog, "active_scheme_id", None)
    if scheme_id is None:
        return
    session = SessionLocal()
    try:
        replace_goals_from_tree(session, scheme_id, dialog.root)
    finally:
        session.close()


def _help_text():
    return "\n".join(
        [
            "Команды:",
            "- помощь / команды",
            "- цели / дерево (перейти к целям)",
            "- осэ / посчитать осэ (перейти к ОСЭ)",
            "- добавить классификатор <имя>",
            "- добавить элемент <значение> в классификатор <имя>",
            "- покажи классификаторы",
            "- переименовать цель <старое> в <новое>",
            "- удалить цель <имя|id>",
            "- удалить классификатор <имя>",
            "- удалить фактор <имя>",
            "- удалить осэ",
        ]
    )

def try_parse_edit_command(text):
    s = text.strip()

    if s.lower() in ["помощь", "help", "команды", "?"]:
        return ("help",)

    if s.lower() in ["завершить", "конец", "finish", "stop"]:
        return ("finish",)

    if s.lower() in ["цели", "цель", "дерево", "добавить цели", "добавить цель"]:
        return ("go_tree",)

    if s.lower() in ["осэ", "ose", "посчитать осэ", "считать осэ"]:
        return ("go_ose",)

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

    m = re.match(r'переименовать\s+цель\s+"(.+?)"\s+в\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'переименовать\s+цель\s+(.+?)\s+в\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("rename_goal", m.group(1), m.group(2))

    m = re.match(r'удалить\s+цель\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'удалить\s+цель\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("delete_goal", m.group(1))

    m = re.match(r'удалить\s+классификатор\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'удалить\s+классификатор\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("delete_classifier", m.group(1))

    m = re.match(r'удалить\s+фактор\s+"(.+?)"\s*$', s, flags=re.IGNORECASE)
    if not m:
        m = re.match(r'удалить\s+фактор\s+(.+?)\s*$', s, flags=re.IGNORECASE)
    if m:
        return ("delete_factor", m.group(1))

    if s.lower() in ["удалить осэ", "очистить осэ", "сбросить осэ"]:
        return ("clear_ose",)

    if s.lower() in ["покажи классификаторы", "показать классификаторы"]:
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

    if dialog.state == "clf_pair_decide" and s.lower() in ["следующее сочетание", "следующее", "пропустить", "продолжить"]:
        return ("clf_next_pair",)

    if dialog.state == "clf_pair_decide" and s.lower() in ["стоп классификаторы", "остановить классификаторы"]:
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
    if not name:
        return edit_response("Введите название классификатора.")

    dialog.phase = "adpacf"

    if dialog.state not in ("clf_name", "clf_items", "clf_more"):
        dialog.clfs = []
        dialog.clf_tmp_name = None
        dialog.clf_parent_goal = None
        dialog.clf_indices = None
        dialog.clf_level = 1
        dialog.clf_done = False

    dialog.clf_tmp_name = name
    dialog.state = "clf_items"

    return DialogResponse(
        phase="adpacf",
        state="clf_items",
        question=(
            f"Классификатор = '{dialog.clf_tmp_name}'.\n"
            "Введите элементы через запятую (ключевые слова):"
        ),
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
        message=None,
    )


def cmd_add_classifier_item(cmd):
    value = cmd[1].strip()
    clf_name = cmd[2].strip()
    scheme_id = dialog.active_scheme_id
    session = SessionLocal()
    try:
        clf = get_classifier_with_items(session, scheme_id, clf_name)
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
    session = SessionLocal()
    try:
        c1 = get_classifier_with_items(session, scheme_id, c1_name)
        c2 = get_classifier_with_items(session, scheme_id, c2_name)
    finally:
        session.close()

    if not c1 or not c2:
        return edit_response("Один из классификаторов не найден.")

    dialog.clf_pairs = [(a.value, b.value) for a in c1.items for b in c2.items]
    dialog.clf_pair_idx = 0
    dialog.state = "clf_pair_decide"

    x, y = dialog.clf_pairs[0]
    return edit_response(f"{x} / {y} — добавить как подцель? (да/нет)")

def cmd_clf_next_pair(_cmd):
    dialog.clf_pair_idx += 1
    if dialog.clf_pair_idx >= len(dialog.clf_pairs):
        dialog.state = "ask_add_subgoal"
        dialog.clf_pairs = []
        return edit_response("Сочетания закончились.")

    x, y = dialog.clf_pairs[dialog.clf_pair_idx]
    return edit_response(f"{x} / {y} — добавить? (да/нет)", state="clf_pair_decide")


def cmd_clf_stop(_cmd):
    dialog.clf_pairs = []
    dialog.clf_parent_goal = None
    dialog.state = "ask_add_subgoal"
    return edit_response("Режим классификаторов остановлен.")


def menu_question():
    return "Введите команду:\n" + _help_text()


def cmd_help(_cmd):
    dialog.phase = "menu"
    dialog.state = "menu"
    return edit_response(menu_question())


def cmd_go_tree(_cmd):
    dialog.phase = "adpacf"
    dialog.state = "ask_add_subgoal" if dialog.root else "ask_root"

    if dialog.state == "ask_root":
        return edit_response("Введите главную цель:")

    return edit_response(f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)")


def cmd_go_ose(_cmd):
    if not dialog.root:
        return edit_response("Сначала задайте дерево целей.")
    dialog.phase = "adpose"
    dialog.state = "ask_factor_name"
    return edit_response("Введите название фактора:")


def cmd_rename_goal(cmd):
    old_name = cmd[1].strip().lower()
    new_name = cmd[2].strip()
    if not dialog.root:
        return edit_response("Дерево целей не задано.")
    if not new_name:
        return edit_response("Пустое имя цели.")
    if new_name.lower() in dialog.used_names:
        return edit_response("Название уже существует.")
    node = dialog.goal_by_name.get(old_name)
    if not node:
        return edit_response("Цель не найдена.")
    node.name = new_name
    _rebuild_goal_maps()
    _persist_tree()
    _recalc_ose_results()
    return edit_response("Цель переименована.")


def _find_goal_token(token: str):
    t = token.strip()
    if not dialog.root:
        return None
    if t.isdigit():
        gid = int(t)
        for g in collect_goals(dialog.root):
            if g.id == gid:
                return g
        return None
    return dialog.goal_by_name.get(t.lower())


def _persist_ose():
    scheme_id = getattr(dialog, "active_scheme_id", None)
    if scheme_id is None:
        return
    session = SessionLocal()
    try:
        replace_ose_results(session, scheme_id, _strip_summaries(dialog.factors_results))
    finally:
        session.close()


def cmd_delete_goal(cmd):
    token = cmd[1]
    node = _find_goal_token(token)
    if not node:
        return edit_response("Цель не найдена.")
    if node.parent is None:
        return edit_response("Нельзя удалить корневую цель.")
    node.parent.children = [ch for ch in node.parent.children if ch is not node]
    if dialog.current_node is node:
        dialog.current_node = node.parent
    _rebuild_goal_maps()
    _persist_tree()
    base = [r for r in _strip_summaries(dialog.factors_results) if str(r.get("goal", "")).lower() != node.name.lower()]
    dialog.factors_results = base
    dialog.factor_set = set(r.get("factor") for r in base if r.get("factor"))
    _recalc_ose_results()
    return edit_response("Цель удалена.")


def cmd_delete_classifier(cmd):
    name = cmd[1].strip()
    scheme_id = dialog.active_scheme_id
    if scheme_id is None:
        return edit_response("Активная схема не выбрана.")
    session = SessionLocal()
    try:
        ok = delete_classifier(session, scheme_id, name)
    except Exception:
        session.rollback()
        return edit_response("Не удалось удалить классификатор.")
    finally:
        session.close()
    if not ok:
        return edit_response("Классификатор не найден.")
    return edit_response("Классификатор удалён.")

def cmd_clear_ose(_cmd):
    dialog.factors_results = []
    dialog.factor_set = set()
    dialog.current_factor_name = None
    dialog._ose_goal = None
    dialog._p = None
    dialog._q = None
    _persist_ose()
    return edit_response("ОСЭ очищено.")

def cmd_delete_factor(cmd):
    name = cmd[1].strip().lower()
    base = _strip_summaries(dialog.factors_results)
    base2 = [r for r in base if str(r.get("factor", "")).lower() != name]
    dialog.factors_results = base2
    dialog.factor_set = set(r.get("factor") for r in base2 if r.get("factor"))
    _recalc_ose_results()
    _persist_ose()
    return edit_response("Фактор удалён.")

_COMMANDS = {
    "help": cmd_help,
    "go_tree": cmd_go_tree,
    "go_ose": cmd_go_ose,
    "rename_goal": cmd_rename_goal,
    "delete_goal": cmd_delete_goal,
    "delete_classifier": cmd_delete_classifier,
    "delete_factor": cmd_delete_factor,
    "clear_ose": cmd_clear_ose,

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