import os
import base64
import secrets

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from api.router import router

app = FastAPI(
    title="PlanFactor API",
    description="АДПАЦФ + АДП ОСЭ — диалоговый интерфейс",
    version="1.0.0",
)

USERNAME = os.getenv("AUTH_USER")
PASSWORD = os.getenv("AUTH_PASS")

if USERNAME is None or PASSWORD is None:
    raise RuntimeError("AUTH_USER и AUTH_PASS не установлены.")

@app.middleware("http")
async def basic_auth_middleware(request: Request, call_next):
    if request.method == "HEAD":
        return await call_next(request)
    if request.url.path.startswith("/static"):
        return await call_next(request)

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    scheme, _, encoded = auth_header.partition(" ")
    if scheme.lower() != "basic":
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    if not (secrets.compare_digest(username, USERNAME) and secrets.compare_digest(password, PASSWORD)):
        return Response(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})

    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="frontend"), name="static")

app.include_router(router)

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")
