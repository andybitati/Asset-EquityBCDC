import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Dict
from dotenv import load_dotenv

load_dotenv()
security = HTTPBearer()

DEFAULT_USERS: Dict[str, str] = {
    "admin": "StrongPassword123!",
    "user": "Password2026!"
}

USERS: Dict[str, str] = {}
for item in os.getenv("ASSET_EQUITY_USERS", ",".join(f"{u}:{p}" for u, p in DEFAULT_USERS.items())).split(","):
    if ":" in item:
        username, password = item.split(":", 1)
        USERS[username.strip()] = password.strip()

TOKENS: Dict[str, str] = {}


def authenticate_user(username: str, password: str) -> str:
    expected = USERS.get(username)
    if expected and expected == password:
        token = f"token-{username}-secure"
        TOKENS[token] = username
        return token
    raise HTTPException(status_code=401, detail="Identifiants invalides")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    username = TOKENS.get(token)
    if not username:
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")
    return username
