import math
from core.dialog_state import dialog
from core.schemas import DialogResponse
from models.goal import serialize_tree


def handle_adpose(ans: str) -> DialogResponse:
    text = ans.strip()

    # ============================================================
    #  1) Команда завершения ОСЭ
    # ============================================================
    if text.lower() in ["завершить", "конец", "finish", "stop"]:
        dialog.state = "finish_ose"
        return DialogResponse(
            phase="adpose",
            state="finish_ose",
            question="Оценка факторов завершена.",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    # ============================================================
    #  2) Ввод названия фактора
    # ============================================================
    if dialog.state == "ask_factor_name":
        # пустой ввод → тоже считаем завершением ОСЭ
        if text == "":
            dialog.state = "finish_ose"
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

        dialog.current_factor_name = text
        dialog.factor_set.add(text.lower())
        dialog.used_names.add(text.lower())
        dialog.current_goal_idx = 0
        dialog.state = "ask_p"

        goal = dialog.goals_ordered[0]

        return DialogResponse(
            phase="adpose",
            state="ask_p",
            question=f"Введите p (0..1) для цели '{goal.name}':",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    # ============================================================
    #  3) Ввод p
    # ============================================================
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
                question="p не может быть равно 1, иначе формула даёт бесконечность. Введите p < 1:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        dialog._p = p
        goal = dialog.goals_ordered[dialog.current_goal_idx]
        dialog.state = "ask_q"

        return DialogResponse(
            phase="adpose",
            state="ask_q",
            question=f"Введите q (0..1) для цели '{goal.name}':",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    # ============================================================
    #  4) Ввод q и вычисление H
    # ============================================================
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

        if q == 0:
            return DialogResponse(
                phase="adpose",
                state="ask_q",
                question="q = 0 означает отсутствие влияния. Введите q > 0:",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        p = dialog._p
        goal = dialog.goals_ordered[dialog.current_goal_idx]

        # безопасный расчёт H
        if p <= 0 or q <= 0:
            H = 0.0
        else:
            try:
                H = -q * math.log(1 - p)
            except ValueError:
                H = 0.0

        dialog.factors_results.append({
            "goal": goal.name,
            "factor": dialog.current_factor_name,
            "H": round(H, 4),
        })

        dialog.current_goal_idx += 1

        # все цели обработаны → просим следующий фактор
        if dialog.current_goal_idx >= len(dialog.goals_ordered):
            dialog.state = "ask_factor_name"
            return DialogResponse(
                phase="adpose",
                state="ask_factor_name",
                question="Введите название следующего фактора (или 'завершить'):",
                tree=serialize_tree(dialog.root),
                ose_results=dialog.factors_results,
            )

        # иначе → следующая цель
        next_goal = dialog.goals_ordered[dialog.current_goal_idx]
        dialog.state = "ask_p"

        return DialogResponse(
            phase="adpose",
            state="ask_p",
            question=f"Введите p (0..1) для цели '{next_goal.name}':",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    # ============================================================
    #  5) Финальное состояние
    # ============================================================
    if dialog.state == "finish_ose":
        return DialogResponse(
            phase="adpose",
            state="finish_ose",
            question="Оценка факторов завершена.",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )

    # fallback
    return DialogResponse(
        phase="adpose",
        state="error",
        question="Неизвестное состояние диалога в АДП ОСЭ.",
        tree=serialize_tree(dialog.root),
        ose_results=dialog.factors_results,
    )
