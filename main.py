import os
import base64
import secrets

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.router import router


app = FastAPI(
    title="PlanFactor API",
    description="АДПАЦФ + АДП ОСЭ — диалоговый интерфейс",
    version="1.0.0",
)

# ------------------------------
# BASIC AUTH через ENV переменные
# ------------------------------

USERNAME = os.getenv("AUTH_USER")
PASSWORD = os.getenv("AUTH_PASS")

if USERNAME is None or PASSWORD is None:
    raise RuntimeError(
        "Ошибка: переменные окружения AUTH_USER и AUTH_PASS не установлены!\n"
        "Перед деплоем на Render/Railway добавь их в Settings → Environment."
    )


@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):

    # Разрешить статику (если появится)
    if request.url.path.startswith("/static"):
        return await call_next(request)

    # Разрешить публичные точки входа (если нужны)
    # Если хочешь закрыть ВСЁ — удали эту проверку
    if request.url.path in ["/dialog/start"]:
        return await call_next(request)

    # Проверка заголовка
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )

    scheme, _, encoded = auth_header.partition(" ")

    if scheme.lower() != "basic":
        raise HTTPException(
            status_code=401,
            detail="Invalid auth scheme",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Декодирование base64 → username:password
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Проверка логина и пароля
    if not (
        secrets.compare_digest(username, USERNAME)
        and secrets.compare_digest(password, PASSWORD)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "API работает. Используйте /dialog/start и /dialog/answer.",
    }
