import math
from core.dialog_state import dialog
from core.schemas import DialogResponse
from db.goal import serialize_tree


def _strip_summaries(rows: list[dict]) -> list[dict]:
    return [r for r in (rows or []) if str(r.get("factor", "")).startswith("ΣH ") is False]


def _append_goal_summaries(rows: list[dict], root) -> list[dict]:
    """
    rows: базовые строки (goal, factor, p, q, H)
    root: корень дерева целей
    """

    # 1) сумма H по факторам для каждой цели
    base_sum: dict[str, float] = {}
    for r in rows:
        try:
            h = float(r.get("H", 0) or 0)
        except Exception:
            h = 0.0
        g = r.get("goal", "") or ""
        base_sum[g] = base_sum.get(g, 0.0) + h

    # 2) карта детей: goal_name -> [child_name, ...]
    children: dict[str, list[str]] = {}

    def walk(n):
        if not n:
            return
        children.setdefault(n.name, [])
        for ch in getattr(n, "children", []) or []:
            children.setdefault(n.name, []).append(ch.name)
            walk(ch)

    walk(root)

    # 3) рекурсивная свёртка по поддереву
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

    # 4) собрать результат: сначала базовые строки, затем ΣH
    out = list(rows)

    for g, s in base_sum.items():
        out.append({"goal": g, "factor": "ΣH (по цели)", "p": "", "q": "", "H": round(s, 4)})

    for g, s in total_sum.items():
        out.append({"goal": g, "factor": "ΣH (по поддереву)", "p": "", "q": "", "H": round(s, 4)})

    return out


def handle_adpose(ans: str) -> DialogResponse:
    text = ans.strip()

    if text.lower() in ["завершить", "конец", "finish", "stop"]:
        dialog.state = "finish_ose"
        return DialogResponse(
            phase="adpose",
            state="finish_ose",
            question=(
                "Оценка факторов завершена.\n\n"
                "Доступные функции:\n"
                "Схемы:\n"
                "- создание схемы (кнопка/действие в UI)\n"
                "- удаление схемы\n"
                "- переключение схем\n\n"
                "Дерево целей (АДПАЦФ):\n"
                "- ввод главной цели\n"
                "- добавление подцелей (да/нет)\n\n"
                "Редактирование через чат:\n"
                "- переименовать цель \"A\" в \"B\"\n"
                "- удалить цель \"A\"\n\n"
                "Классификаторы:\n"
                "- добавь классификатор \"X\"\n"
                "- добавь элемент \"A\" в классификатор \"X\"\n"
                "- покажи классификаторы\n"
                "- начать классификаторы для цели \"Y\"\n"
                "- используй классификаторы \"X\" и \"Z\"\n"
                "- следующее сочетание\n"
                "- стоп классификаторы\n\n"
                "ОСЭ:\n"
                "- ввод факторов\n"
                "- ввод p и q по целям\n"
                "- расчёт H и вывод таблицы результатов"
            ),
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    if dialog.state == "ask_factor_name":
        if text == "":
            dialog.state = "finish_ose"
            dialog.factors_results = _append_goal_summaries(
                _strip_summaries(dialog.factors_results),
                dialog.root,
            )
            return DialogResponse(
                phase="adpose",
                state="finish_ose",
                question="Оценка факторов завершена.",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if text.lower() in dialog.used_names:
            return DialogResponse(
                phase="adpose",
                state="ask_factor_name",
                question="Фактор с таким названием уже существует. Введите другое название:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        dialog.factor_name = text
        dialog.factor_set.add(text.lower())
        dialog.used_names.add(text.lower())

        dialog.state = "ask_goal"
        return DialogResponse(
            phase="adpose",
            state="ask_goal",
            question="Введите название цели, для которой оцениваем этот фактор:",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    if dialog.state == "ask_goal":
        raw = text.strip()
        goal = None

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

            goal = _find_by_id(dialog.root)

        if goal is None:
            goal = dialog.goal_by_name.get(raw.lower())

        if goal is None:
            return DialogResponse(
                phase="adpose",
                state="ask_goal",
                question="Цель не найдена. Введите название цели точно как в дереве:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        dialog._ose_goal = goal
        dialog.state = "ask_p"
        return DialogResponse(
            phase="adpose",
            state="ask_p",
            question=f"Введите p (0..1) для цели '{goal.name}':",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    if dialog.state == "ask_p":
        try:
            p = float(text)
        except ValueError:
            return DialogResponse(
                phase="adpose",
                state="ask_p",
                question="Некорректный ввод. Введите p (число от 0 до 1):",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if p < 0 or p > 1:
            return DialogResponse(
                phase="adpose",
                state="ask_p",
                question="p должно быть числом от 0 до 1. Введите p ещё раз:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if p == 1:
            return DialogResponse(
                phase="adpose",
                state="ask_p",
                question="p не может быть равно 1 (log(0)). Введите p < 1:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        dialog._p = p
        dialog.state = "ask_q"
        return DialogResponse(
            phase="adpose",
            state="ask_q",
            question=f"Введите q (0..1) для цели '{dialog._ose_goal.name}':",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    if dialog.state == "ask_q":
        try:
            q = float(text)
        except ValueError:
            return DialogResponse(
                phase="adpose",
                state="ask_q",
                question="Некорректный ввод. Введите q (число от 0 до 1):",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        if q < 0 or q > 1:
            return DialogResponse(
                phase="adpose",
                state="ask_q",
                question="q должно быть от 0 до 1. Введите q ещё раз:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        p = dialog._p
        goal = dialog._ose_goal

        if p <= 0 or q <= 0:
            H = 0.0
        else:
            try:
                H = -q * math.log(1 - p)
            except ValueError:
                H = 0.0

        base = _strip_summaries(dialog.factors_results)
        base.append(
            {
                "goal": goal.name,
                "factor": dialog.factor_name,
                "p": round(p, 4),
                "q": round(q, 4),
                "H": round(H, 4),
            }
        )

        dialog.factors_results = _append_goal_summaries(base, dialog.root)

        dialog.state = "ask_more_goal_for_factor"
        return DialogResponse(
            phase="adpose",
            state="ask_more_goal_for_factor",
            question="Оценить этот же фактор для другой цели? (да/нет)",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    if dialog.state == "ask_more_goal_for_factor":
        a = text.lower()
        if a == "да":
            dialog.state = "ask_goal"
            return DialogResponse(
                phase="adpose",
                state="ask_goal",
                question="Введите название следующей цели для этого фактора:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        dialog.state = "ask_factor_name"
        return DialogResponse(
            phase="adpose",
            state="ask_factor_name",
            question="Введите название следующего фактора (или пустую строку / 'завершить'):",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    if dialog.state == "finish_ose":
        return DialogResponse(
            phase="adpose",
            state="finish_ose",
            question="Оценка факторов завершена.",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    return DialogResponse(
        phase="adpose",
        state="error",
        question="Неизвестное состояние диалога в АДП ОСЭ.",
        tree=serialize_tree(dialog.root),
        ose_results=dialog.factors_results,
    )
