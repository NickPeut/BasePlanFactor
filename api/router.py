from fastapi import APIRouter
from core.dialog_state import dialog
from core.schemas import AnswerRequest, DialogResponse
from models.goal import serialize_tree
from api.adpacf import handle_adpacf
from api.adpose import handle_adpose
from api.edit_commands import try_parse_edit_command, handle_edit_command

router = APIRouter()


@router.post("/dialog/start", response_model=DialogResponse)
def start_dialog():
    dialog.__init__()
    return DialogResponse(
        phase="adpacf",
        state="ask_root",
        question="Введите главную цель:",
        tree=[]
    )


@router.post("/dialog/answer", response_model=DialogResponse)
def answer(req: AnswerRequest):
    text = req.answer.strip()

    # 1. проверка на команды редактирования
    cmd = try_parse_edit_command(text)
    if cmd:
        return handle_edit_command(cmd)

    # 2. обычный диалог
    if dialog.phase == "adpacf":
        return handle_adpacf(text)

    if dialog.phase == "adpose":
        return handle_adpose(text)

    return DialogResponse(
        phase=dialog.phase,
        state="error",
        question="Ошибка состояния.",
        tree=serialize_tree(dialog.root)
    )
