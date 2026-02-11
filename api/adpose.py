import math
from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import serialize_tree, collect_goals
from db.goals import replace_ose_results
from db.session import SessionLocal


def _strip_summaries(rows: list[dict]) -> list[dict]:
    return [r for r in (rows or []) if not str(r.get("factor", "")).startswith("ΣH ")]


def calculate_ose(p: float, q: float) -> float:
    if p <= 0 or q <= 0:
        return 0.0
    if p >= 1:
        return 0.0
    try:
        return -q * math.log(1 - p)
    except ValueError:
        return 0.0


def _append_goal_summaries(rows: list[dict], root) -> list[dict]:
    base_sum: dict[str, float] = {}
    for r in rows:
        try:
            h = float(r.get("H", 0) or 0)
        except Exception:
            h = 0.0
        g = r.get("goal", "") or ""
        base_sum[g] = base_sum.get(g, 0.0) + h

    children: dict[str, list[str]] = {}

    def walk(n):
        if not n:
            return
        children.setdefault(n.name, [])
        for ch in getattr(n, "children", []) or []:
            children.setdefault(n.name, []).append(ch.name)
            walk(ch)

    walk(root)

    total_sum: dict[str, float] = {}

    def fold(goal_name: str) -> float:
        if goal_name in total_sum:
            return total_sum[goal_name]

        s = base_sum.get(goal_name, 0.0)
        for ch in children.get(goal_name, []):
            s += fold(ch)

        total_sum[goal_name] = s
        return s

    for g in children.keys():
        fold(g)

    out = list(rows)

    for g, s in base_sum.items():
        out.append({"goal": g, "factor": "ΣH (по цели)", "p": "", "q": "", "H": round(s, 4)})

    for g, s in total_sum.items():
        out.append({"goal": g, "factor": "ΣH (по поддереву)", "p": "", "q": "", "H": round(s, 4)})

    return out


def _resp(state: str, question: str) -> DialogResponse:
    return DialogResponse(
        phase="adpose",
        state=state,
        question=question,
        tree=serialize_tree(dialog.root),
        ose_results=dialog.factors_results,
    )


def _finish_ose() -> DialogResponse:
    dialog.state = "finish_ose"
    dialog.factors_results = _append_goal_summaries(_strip_summaries(dialog.factors_results), dialog.root)
    return _resp(
        "finish_ose",
        "ОСЭ завершена.\n"
        "Введите 'команды' чтобы увидеть доступные действия.",
    )


def _handle_ask_factor_name(text: str) -> DialogResponse:
    if text == "" or text.lower() in ["завершить", "конец", "finish", "stop"]:
        return _finish_ose()

    if text.lower() in dialog.factor_set:
        return _resp("ask_factor_name", "Фактор с таким названием уже существует. Введите другое название:")

    dialog.current_factor_name = text
    dialog.factor_set.add(text.lower())

    dialog.ose_goals = collect_goals(dialog.root)
    dialog.ose_goal_idx = 0

    if not dialog.ose_goals:
        dialog.state = "ask_factor_name"
        return _resp("ask_factor_name", "Нет целей-листьев для оценки. Введите название фактора ещё раз:")

    dialog._ose_goal = dialog.ose_goals[0]
    dialog._p = None
    dialog._q = None
    dialog.state = "ask_p"
    return _resp("ask_p", f"Введите p (0..1) для цели '{dialog._ose_goal.name}':")


def _handle_ask_p(text: str) -> DialogResponse:
    try:
        p = float(text)
    except ValueError:
        return _resp("ask_p", "Некорректный ввод. Введите p (число от 0 до 1):")

    if p < 0 or p > 1:
        return _resp("ask_p", "p должно быть числом от 0 до 1. Введите p ещё раз:")

    if p == 1:
        return _resp("ask_p", "p не может быть равно 1 (log(0)). Введите p < 1:")

    dialog._p = p
    dialog.state = "ask_q"
    return _resp("ask_q", f"Введите q (0..1) для цели '{dialog._ose_goal.name}':")


def _persist_ose():
    scheme_id = getattr(dialog, "active_scheme_id", None)
    if scheme_id is None:
        return
    session = SessionLocal()
    try:
        replace_ose_results(session, scheme_id, _strip_summaries(dialog.factors_results))
    finally:
        session.close()


def _handle_ask_q(text: str) -> DialogResponse:
    try:
        q = float(text)
    except ValueError:
        return _resp("ask_q", "Введите q числом (0..1):")

    if not (0 <= q <= 1):
        return _resp("ask_q", "q должно быть в диапазоне [0..1]:")

    dialog._q = q

    p = dialog._p
    H = calculate_ose(p, q)

    dialog.factors_results.append(
        {
            "goal": dialog._ose_goal.name,
            "factor": dialog.current_factor_name,
            "p": p,
            "q": q,
            "H": H,
        }
    )

    nxt = dialog.ose_goal_idx + 1
    if nxt < len(dialog.ose_goals):
        dialog.ose_goal_idx = nxt
        dialog._ose_goal = dialog.ose_goals[nxt]
        dialog._p = None
        dialog._q = None
        dialog.state = "ask_p"
        return _resp("ask_p", f"Введите p (0..1) для цели '{dialog._ose_goal.name}':")

    dialog.state = "ask_factor_name"
    dialog._ose_goal = None
    dialog._p = None
    dialog._q = None

    return _resp("ask_factor_name", "Введите название следующего фактора (или пустую строку / 'завершить'):")


_HANDLERS = {
    "ask_factor_name": _handle_ask_factor_name,
    "ask_p": _handle_ask_p,
    "ask_q": _handle_ask_q,
}


def handle_adpose(ans: str) -> DialogResponse:
    text = ans.strip()

    if dialog.state == "finish_ose":
        return _resp("finish_ose", "ОСЭ завершена.\nВведите 'команды' чтобы увидеть доступные действия.")

    handler = _HANDLERS.get(dialog.state)
    if not handler:
        return _resp("error", "Неизвестное состояние диалога в АДП ОСЭ.")

    return handler(text)
