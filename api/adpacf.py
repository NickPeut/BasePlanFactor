from core.dialog_state import dialog
from core.schemas import DialogResponse

from db.goal import GoalNode, serialize_tree, collect_goals
from db.session import SessionLocal
from db.goals import get_classifier_with_items, create_classifier, add_classifier_item, replace_goals_from_tree


def _persist_tree():
    scheme_id = getattr(dialog, "active_scheme_id", None)
    if scheme_id is None:
        return
    session = SessionLocal()
    try:
        replace_goals_from_tree(session, scheme_id, dialog.root)
    finally:
        session.close()


def handle_adpacf(ans: str) -> DialogResponse:
    text = ans.strip()

    if dialog.state == "ask_root":
        if not text:
            return DialogResponse(
                phase="adpacf",
                state="ask_root",
                question="Введите название главной цели:",
                tree=[],
            )

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

    if dialog.state == "ask_add_subgoal":
        answer_low = text.lower()

        if answer_low == "да":
            if dialog.current_node.level >= dialog.max_level:
                return DialogResponse(
                    phase="adpacf",
                    state="ask_add_subgoal",
                    question=(
                        f"Достигнут максимальный уровень ({dialog.max_level}). "
                        f"Подцель для '{dialog.current_node.name}' добавить нельзя. "
                        "Ответьте 'нет', чтобы вернуться к родительской цели или завершить ввод дерева."
                    ),
                    tree=serialize_tree(dialog.root),
                )

            dialog.state = "ask_subgoal_name"
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question=f"Введите название подцели для '{dialog.current_node.name}':",
                tree=serialize_tree(dialog.root),
            )

        if dialog.current_node.parent:
            dialog.current_node = dialog.current_node.parent
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        if not getattr(dialog, "clf_done", False):
            dialog.state = "clf_name"
            dialog.clfs = []
            dialog.clf_tmp_name = None
            dialog.clf_parent_goal = None
            dialog.clf_indices = None
            dialog.clf_level = 1

            return DialogResponse(
                phase="adpacf",
                state="clf_name",
                question=(
                    "Введите название классификатора (признака структуризации)."
                ),
                tree=serialize_tree(dialog.root),
            )

        dialog.phase = "adpose"
        dialog.state = "ask_factor_name"
        dialog.goals_ordered = collect_goals(dialog.root)

        return DialogResponse(
            phase="adpose",
            state="ask_factor_name",
            question="Введите название фактора (или 'завершить'):",
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "ask_subgoal_name":
        if not text:
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question="Название не может быть пустым. Введите подцель:",
                tree=serialize_tree(dialog.root),
            )

        if text.lower() in dialog.used_names:
            return DialogResponse(
                phase="adpacf",
                state="ask_subgoal_name",
                question="Название уже используется. Введите другое название подцели:",
                tree=serialize_tree(dialog.root),
            )

        child = dialog.current_node.add_child(text)
        dialog.current_node = child

        dialog.used_names.add(text.lower())
        dialog.goal_by_name[text.lower()] = child

        dialog.state = "ask_add_subgoal"
        _persist_tree()
        return DialogResponse(
            phase="adpacf",
            state="ask_add_subgoal",
            question=f"Добавить подцель для '{child.name}'? (да/нет)",
            tree=serialize_tree(dialog.root),
        )

    def _find_goal(raw: str):
        parent = None
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

            parent = _find_by_id(dialog.root)

        if parent is None:
            parent = dialog.goal_by_name.get(raw.lower())

        return parent

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

    if dialog.state == "clf_name":
        if not text:
            return DialogResponse(
                phase="adpacf",
                state="clf_name",
                question="Введите название классификатора:",
                tree=serialize_tree(dialog.root),
            )

        dialog.clf_tmp_name = text
        dialog.state = "clf_items"
        return DialogResponse(
            phase="adpacf",
            state="clf_items",
            question=(
                f"Классификатор = '{dialog.clf_tmp_name}'.\n"
                "Введите элементы через запятую (ключевые слова):"
            ),
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "clf_items":
        items = [x.strip() for x in text.split(",") if x.strip()]
        if not items:
            return DialogResponse(
                phase="adpacf",
                state="clf_items",
                question="Введите хотя бы один элемент через запятую:",
                tree=serialize_tree(dialog.root),
            )

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

        dialog.clfs.append({
            "name": dialog.clf_tmp_name,
            "items": all_items,
            "level": dialog.clf_level,
        })
        dialog.clf_tmp_name = None
        dialog.state = "clf_more"
        r = 1
        for c in dialog.clfs:
            r *= max(1, len(c["items"]))

        return DialogResponse(
            phase="adpacf",
            state="clf_more",
            question=(
                f"Классификатор добавлен. Текущее число сочетаний R = {r}.\n"
                "Добавить ещё классификатор? (да/нет)"
            ),
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "clf_more":
        a = text.lower()
        if a == "да":
            dialog.clf_level += 1
            dialog.state = "clf_name"
            return DialogResponse(
                phase="adpacf",
                state="clf_name",
                question="Введите название следующего классификатора:",
                tree=serialize_tree(dialog.root),
            )

        if len(dialog.clfs) < 2:
            dialog.state = "clf_name"
            return DialogResponse(
                phase="adpacf",
                state="clf_name",
                question="Нужно минимум 2 классификатора. Введите название следующего:",
                tree=serialize_tree(dialog.root),
            )

        dialog.state = "clf_parent_goal"
        return DialogResponse(
            phase="adpacf",
            state="clf_parent_goal",
            question="Введите название цели-родителя для структуризации:",
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "clf_parent_goal":
        parent = _find_goal(text.strip())
        if parent is None:
            return DialogResponse(
                phase="adpacf",
                state="clf_parent_goal",
                question="Цель не найдена. Введите название цели точно как в дереве:",
                tree=serialize_tree(dialog.root),
            )

        dialog.clf_parent_goal = parent
        dialog.clf_indices = [0 for _ in dialog.clfs]
        dialog.state = "clf_combo_decide"

        combo = _clf_combo_text()
        combo_s = " / ".join(combo)
        return DialogResponse(
            phase="adpacf",
            state="clf_combo_decide",
            question=f"Сочетание ⟨{combo_s}⟩ включить как подцель? (да/нет)",
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "clf_combo_decide":
        answer_low = text.lower()
        if answer_low not in ("да", "нет"):
            combo = _clf_combo_text()
            combo_s = " / ".join(combo)
            return DialogResponse(
                phase="adpacf",
                state="clf_combo_decide",
                question=f"Сочетание ⟨{combo_s}⟩ включить как подцель? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        parent = dialog.clf_parent_goal
        if parent:
            combo = _clf_combo_text()
            name = " / ".join(combo)
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
            dialog.state = "after_classifiers"
            return DialogResponse(
                phase="adpacf",
                state="after_classifiers",
                question=(
                    "Структуризация по классификаторам завершена.\n"
                    "Введите:\n"
                    "- 'классификаторы' чтобы построить уровень для другой цели\n"
                    "- 'осэ' чтобы перейти к оценке факторов\n"
                    "- 'дерево' чтобы вернуться к ручному добавлению подцелей"
                ),
                tree=serialize_tree(dialog.root),
            )

        combo = _clf_combo_text()
        combo_s = " / ".join(combo)
        return DialogResponse(
            phase="adpacf",
            state="clf_combo_decide",
            question=f"Сочетание ⟨{combo_s}⟩ включить как подцель? (да/нет)",
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "clf_pair_decide":
        answer_low = text.lower()

        if answer_low not in ("да", "нет"):
            a, b = dialog.clf_pairs[dialog.clf_pair_idx]
            return DialogResponse(
                phase="adpacf",
                state="clf_pair_decide",
                question=f"Сочетание ⟨{a}, {b}⟩ включить как подцель? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        parent = dialog.clf_parent_goal
        if not parent:
            dialog.state = "ask_add_subgoal"
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        a, b = dialog.clf_pairs[dialog.clf_pair_idx]
        name = f"{a} / {b}"

        if answer_low == "да":
            if parent.level < dialog.max_level and name.lower() not in dialog.used_names:
                child = parent.add_child(name)
                dialog.used_names.add(name.lower())
                dialog.goal_by_name[name.lower()] = child
                _persist_tree()

        dialog.clf_pair_idx += 1

        if dialog.clf_pair_idx >= len(dialog.clf_pairs):
            dialog.clf_done = True
            dialog.clf_pairs = []
            dialog.clf_pair_idx = 0
            dialog.clf_parent_goal = None
            dialog.state = "after_classifiers"

            return DialogResponse(
                phase="adpacf",
                state="after_classifiers",
                question=(
                    "Структуризация по классификаторам завершена.\n"
                    "Введите:\n"
                    "- 'классификаторы' чтобы построить уровень для другой цели\n"
                    "- 'осэ' чтобы перейти к оценке факторов\n"
                    "- 'дерево' чтобы вернуться к ручному добавлению подцелей"
                ),
                tree=serialize_tree(dialog.root),
            )

        a, b = dialog.clf_pairs[dialog.clf_pair_idx]
        return DialogResponse(
            phase="adpacf",
            state="clf_pair_decide",
            question=f"Сочетание ⟨{a}, {b}⟩ включить как подцель? (да/нет)",
            tree=serialize_tree(dialog.root),
        )

    if dialog.state == "after_classifiers":
        cmd = text.lower()

        if cmd in ("осэ", "ose", "adpose"):
            dialog.phase = "adpose"
            dialog.state = "ask_factor_name"
            dialog.goals_ordered = collect_goals(dialog.root)
            return DialogResponse(
                phase="adpose",
                state="ask_factor_name",
                question="Введите название фактора (или 'завершить'):",
                tree=serialize_tree(dialog.root),
            )

        if cmd in ("дерево", "tree"):
            dialog.state = "ask_add_subgoal"
            dialog.current_node = dialog.root
            return DialogResponse(
                phase="adpacf",
                state="ask_add_subgoal",
                question=f"Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
                tree=serialize_tree(dialog.root),
            )

        if cmd in ("классификаторы", "классификатор", "cls"):
            dialog.state = "clf_name"
            dialog.clfs = []
            dialog.clf_tmp_name = None
            dialog.clf_parent_goal = None
            dialog.clf_indices = None
            dialog.clf_level = 1
            dialog.clf_done = False

            return DialogResponse(
                phase="adpacf",
                state="clf_name",
                question="Введите название классификатора (признака структуризации):",
                tree=serialize_tree(dialog.root),
            )

        return DialogResponse(
            phase="adpacf",
            state="after_classifiers",
            question="Введите 'классификаторы' или 'осэ' или 'дерево'.",
            tree=serialize_tree(dialog.root),
        )

    return DialogResponse(
        phase="adpacf",
        state="error",
        question="Неизвестное состояние в АДПАЦФ.",
        tree=serialize_tree(dialog.root) if dialog.root else [],
    )