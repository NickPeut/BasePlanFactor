from typing import Optional, Dict

from fastapi import APIRouter

from core.dialog_state import dialog
from core.schemas import AnswerRequest, DialogResponse

from db.session import SessionLocal
from db.goals import get_all_goals
from db.goal import GoalNode, serialize_tree

from api.adpacf import handle_adpacf
from api.adpose import handle_adpose
from api.edit_commands import (
    try_parse_edit_command,
    handle_edit_command,
    handle_edit_flow,
    EDIT_FLOW_STATES,
)

router = APIRouter()


def _load_tree_from_db() -> Optional[GoalNode]:
    session = SessionLocal()
    try:
        goals = get_all_goals(session)
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
                nodes[g.parent_id].children.append(nodes[g.id])

        GoalNode._id_counter = (max(nodes.keys()) + 1) if nodes else 1

        return root
    finally:
        session.close()


@router.get("/goals")
def get_goals():
    root = _load_tree_from_db()
    return serialize_tree(root) if root else []


@router.post("/dialog/start", response_model=DialogResponse)
def start_dialog():
    dialog.__init__()

    root = _load_tree_from_db()
    if root:
        dialog.root = root
        dialog.phase = "adpacf"
        dialog.state = "ask_children"

        return DialogResponse(
            phase=dialog.phase,
            state=dialog.state,
            question="Дерево целей загружено из БД. Можешь продолжать добавлять/редактировать цели.",
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

    if dialog.state in EDIT_FLOW_STATES:
        return handle_edit_flow(text)

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
