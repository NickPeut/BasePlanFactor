from typing import Optional, Dict
from fastapi import APIRouter, Query

from core.dialog_state import dialog
from core.schemas import AnswerRequest, DialogResponse

from db.session import SessionLocal
from db.goal import GoalNode, serialize_tree, collect_goals
from db.goals import get_all_goals
from db.schemes import list_schemes, create_scheme, delete_scheme

from api.adpacf import handle_adpacf
from api.adpose import handle_adpose
from api.edit_commands import (
    try_parse_edit_command,
    handle_edit_command,
)



router = APIRouter(prefix="/api")


def _ensure_active_scheme_id() -> int:
    if not hasattr(dialog, "active_scheme_id"):
        dialog.active_scheme_id = None

    session = SessionLocal()
    try:
        schemes = list_schemes(session)
        if not schemes:
            s = create_scheme(session, "Default")
            schemes = [s]

        if dialog.active_scheme_id is None:
            dialog.active_scheme_id = schemes[0].id

        return dialog.active_scheme_id
    finally:
        session.close()


def _load_tree_from_db(scheme_id: int) -> Optional[GoalNode]:
    session = SessionLocal()
    try:
        goals = get_all_goals(session, scheme_id)
        if not goals:
            return None

        nodes: Dict[int, GoalNode] = {}
        for g in goals:
            node = GoalNode(g.name)
            node.id = g.id
            nodes[g.id] = node

        root: Optional[GoalNode] = None
        for g in goals:
            if g.parent_id is None:
                root = nodes[g.id]
            else:
                parent = nodes.get(g.parent_id)
                if parent:
                    parent.children.append(nodes[g.id])

        GoalNode._id_counter = (max(nodes.keys()) + 1) if nodes else 1

        return root
    finally:
        session.close()

@router.get("/schemes")
def get_schemes():
    session = SessionLocal()
    try:
        items = list_schemes(session)
        return [{"id": s.id, "name": s.name} for s in items]
    finally:
        session.close()

@router.post("/schemes")
def post_scheme(name: str = Query(..., min_length=1)):
    session = SessionLocal()
    try:
        s = create_scheme(session, name)
        if not hasattr(dialog, "active_scheme_id"):
            dialog.active_scheme_id = None
        dialog.active_scheme_id = s.id
        return {"id": s.id, "name": s.name}
    finally:
        session.close()

@router.delete("/schemes/{scheme_id}")
def delete_scheme_route(scheme_id: int):
    session = SessionLocal()
    try:
        delete_scheme(session, scheme_id)

        if getattr(dialog, "active_scheme_id", None) == scheme_id:
            dialog.active_scheme_id = None
            _ensure_active_scheme_id()

        return {"ok": True}
    finally:
        session.close()

@router.get("/schemes/{scheme_id}/goals")
def get_scheme_goals(scheme_id: int):
    root = _load_tree_from_db(scheme_id)
    return serialize_tree(root) if root else []

@router.get("/goals")
def get_goals():
    scheme_id = _ensure_active_scheme_id()
    root = _load_tree_from_db(scheme_id)
    return serialize_tree(root) if root else []

@router.post("/dialog/start", response_model=DialogResponse)
def start_dialog(scheme_id: Optional[int] = Query(None)):
    dialog.__init__()

    if not hasattr(dialog, "active_scheme_id"):
        dialog.active_scheme_id = None

    if scheme_id is not None:
        dialog.active_scheme_id = scheme_id
    else:
        _ensure_active_scheme_id()
    root = _load_tree_from_db(dialog.active_scheme_id)

    if root:
        dialog.root = root
        dialog.current_node = root
        dialog.phase = "adpacf"
        dialog.state = "ask_add_subgoal"

        dialog.used_names = set()
        dialog.goal_by_name = {}

        for n in collect_goals(dialog.root):
            dialog.used_names.add(n.name.lower())
            dialog.goal_by_name[n.name.lower()] = n

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question=f"Схема загружена из БД. Добавить подцель для '{dialog.current_node.name}'? (да/нет)",
            tree=serialize_tree(dialog.root),
            ose_results=dialog.factors_results,
        )


    return DialogResponse(
        phase="adpacf",
        state="ask_root",
        question="Введите главную цель:",
        tree=[],
        ose_results=[],
    )


@router.post("/dialog/answer", response_model=DialogResponse)
def process_answer(req: AnswerRequest):
    text = req.answer.strip()
    if text.lower() in ["завершить", "конец", "finish", "stop"]:
        dialog.state = "idle"
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

    cmd = try_parse_edit_command(text)
    if cmd:
        return handle_edit_command(cmd)

    if dialog.phase == "adpacf":
        return handle_adpacf(text)

    if dialog.phase == "adpose":
        return handle_adpose(text)

    return DialogResponse(
        phase=dialog.phase,
        state="error",
        question="Ошибка состояния диалога.",
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
    )
