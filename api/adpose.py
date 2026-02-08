import math
from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import serialize_tree

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
    return _resp("finish_ose", "Оценка факторов завершена.")


def _handle_ask_factor_name(text: str) -> DialogResponse:
    if text == "":
        return _finish_ose()

    if text.lower() in dialog.used_names:
        return _resp("ask_factor_name", "Фактор с таким названием уже существует. Введите другое название:")

    dialog.current_factor_name = text
    dialog.factor_set.add(text.lower())
    dialog.used_names.add(text.lower())

    dialog.state = "ask_goal"
    return _resp("ask_goal", "Введите название цели, для которой оцениваем этот фактор:")


def _find_goal_by_input(raw: str):
    raw = raw.strip()
    if raw.isdigit():
        target_id = int(raw)

        def _find_by_id(n):
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


def _handle_ask_goal(text: str) -> DialogResponse:
    goal = _find_goal_by_input(text)
    if goal is None:
        return _resp("ask_goal", "Цель не найдена. Введите название цели точно как в дереве:")

    dialog._ose_goal = goal
    dialog.state = "ask_p"
    return _resp("ask_p", f"Введите p (0..1) для цели '{goal.name}':")


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


def _handle_ask_q(text: str) -> DialogResponse:
    try:
        q = float(text)
    except ValueError:
        return _resp("ask_q", "Некорректный ввод. Введите q (число от 0 до 1):")

    if q < 0 or q > 1:
        return _resp("ask_q", "q должно быть от 0 до 1. Введите q ещё раз:")

    p = dialog._p
    goal = dialog._ose_goal

    H = calculate_ose(p, q)

    base = _strip_summaries(dialog.factors_results)
    base.append(
        {
            "goal": goal.name,
            "factor": dialog.current_factor_name,
            "p": round(p, 4),
            "q": round(q, 4),
            "H": round(H, 4),
        }
    )
    dialog.factors_results = _append_goal_summaries(base, dialog.root)

    dialog.state = "ask_more_goal_for_factor"
    return _resp("ask_more_goal_for_factor", "Оценить этот же фактор для другой цели? (да/нет)")


def _handle_ask_more_goal_for_factor(text: str) -> DialogResponse:
    a = text.lower()
    if a == "да":
        dialog.state = "ask_goal"
        return _resp("ask_goal", "Введите название следующей цели для этого фактора:")

    dialog.state = "ask_factor_name"
    return _resp("ask_factor_name", "Введите название следующего фактора (или пустую строку / 'завершить'):")


_HANDLERS = {
    "ask_factor_name": _handle_ask_factor_name,
    "ask_goal": _handle_ask_goal,
    "ask_p": _handle_ask_p,
    "ask_q": _handle_ask_q,
    "ask_more_goal_for_factor": _handle_ask_more_goal_for_factor,
}


def handle_adpose(ans: str) -> DialogResponse:
    text = ans.strip()

    if dialog.state == "finish_ose":
        return _resp("finish_ose", "Оценка факторов завершена.")

    handler = _HANDLERS.get(dialog.state)
    if not handler:
        return _resp("error", "Неизвестное состояние диалога в АДП ОСЭ.")

    return handler(text)
