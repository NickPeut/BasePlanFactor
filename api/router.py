from fastapi import APIRouter

from core.dialog_state import dialog
from core.schemas import AnswerRequest, DialogResponse
from db.goal import serialize_tree
from api.adpacf import handle_adpacf
from api.adpose import handle_adpose
from api.edit_commands import (
    try_parse_edit_command,
    handle_edit_command,
    handle_edit_flow,
    EDIT_FLOW_STATES,
)


router = APIRouter()


@router.post("/dialog/start", response_model=DialogResponse)
def start_dialog():
    dialog.__init__()  # сбрасываем всё состояние
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

    # 1. Если сейчас мы находимся внутри мастера редактирования/добавления —
    #    сначала обрабатываем именно его.
    if dialog.state in EDIT_FLOW_STATES:
        return handle_edit_flow(text)

    # 2. Пытаемся распознать команду редактирования (работает в любом состоянии)
    cmd = try_parse_edit_command(text)
    if cmd:
        return handle_edit_command(cmd)

    # 3. Обычный диалог по фазам
    if dialog.phase == "adpacf":
        return handle_adpacf(text)

    if dialog.phase == "adpose":
        return handle_adpose(text)

    # 4. fallback
    return DialogResponse(
        phase=dialog.phase,
        state="error",
        question="Ошибка состояния диалога.",
        tree=serialize_tree(dialog.root) if dialog.root else [],
        ose_results=dialog.factors_results,
    )
