import os
from fastapi import Header, HTTPException, status

def _auth_enabled() -> bool:
    v = os.getenv("AUTH_ENABLED", "0").strip().lower()
    return v in ("1", "true", "yes", "on")

def require_auth(authorization: str | None = Header(default=None)):
    if not _auth_enabled():
        return

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    token = authorization.removeprefix("Bearer ").strip()
    expected = os.getenv("AUTH_TOKEN", "").strip()

    if not expected or token != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
