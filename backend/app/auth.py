import os
import hashlib
import secrets
import string
from datetime import datetime, timedelta
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Dict, Any
from sqlalchemy import create_engine, text
from .config import load_backend_env

load_backend_env()
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

USER_PROFILES = {
    "admin": {
        "username": "admin",
        "display_name": "Admin Equity",
        "photo_url": "https://ui-avatars.com/api/?name=Admin&background=b60f1e&color=ffffff",
    },
    "user": {
        "username": "user",
        "display_name": "Utilisateur BCDC",
        "photo_url": "https://ui-avatars.com/api/?name=User&background=b60f1e&color=ffffff",
    },
}

PBKDF2_ITERATIONS = int(os.getenv("PASSWORD_HASH_ITERATIONS", "260000"))
SESSION_TTL_MINUTES = int(os.getenv("SESSION_TTL_MINUTES", "60"))
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCK_MINUTES = int(os.getenv("LOGIN_LOCK_MINUTES", "15"))

TOKENS: Dict[str, Dict[str, Any]] = {}
LOGIN_ATTEMPTS: Dict[str, Dict[str, Any]] = {}


def validate_password_policy(password: str) -> bool:
    has_min_length = len(password) >= 8
    has_uppercase = any(char.isupper() for char in password)
    has_digit = any(char.isdigit() for char in password)
    has_special = any(char in string.punctuation for char in password)
    return has_min_length and has_uppercase and has_digit and has_special


def password_policy_message() -> str:
    return (
        "Le mot de passe doit contenir au moins 8 caractères, "
        "une majuscule, un chiffre et un caractère spécial."
    )


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    if stored_hash.startswith("pbkdf2_sha256$"):
        _, iterations, salt, expected = stored_hash.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            int(iterations),
        ).hex()
        return secrets.compare_digest(digest, expected)

    legacy_sha256 = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return secrets.compare_digest(legacy_sha256, stored_hash)


def is_legacy_password_hash(stored_hash: str) -> bool:
    return not stored_hash.startswith("pbkdf2_sha256$")


def create_token(username: str) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)
    TOKENS[token] = {
        "username": username,
        "expires_at": expires_at,
    }
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url, future=True)
        with engine.begin() as conn:
            conn.execute(
                text(
                    "INSERT INTO sessions (token, username, created_at, expires_at) "
                    "VALUES (:token, :username, :created_at, :expires_at)"
                ),
                {
                    "token": token,
                    "username": username,
                    "created_at": datetime.utcnow(),
                    "expires_at": expires_at,
                },
            )
    return token


def login_key(username: str) -> str:
    return username.strip().lower()


def is_login_locked(username: str) -> bool:
    attempt = LOGIN_ATTEMPTS.get(login_key(username))
    if not attempt:
        return False
    locked_until = attempt.get("locked_until")
    if locked_until and datetime.utcnow() < locked_until:
        return True
    if locked_until and datetime.utcnow() >= locked_until:
        LOGIN_ATTEMPTS.pop(login_key(username), None)
    return False


def record_login_failure(username: str) -> None:
    key = login_key(username)
    attempt = LOGIN_ATTEMPTS.setdefault(key, {"count": 0, "locked_until": None})
    attempt["count"] += 1
    if attempt["count"] >= MAX_LOGIN_ATTEMPTS:
        attempt["locked_until"] = datetime.utcnow() + timedelta(minutes=LOGIN_LOCK_MINUTES)


def clear_login_failures(username: str) -> None:
    LOGIN_ATTEMPTS.pop(login_key(username), None)


def get_database_user(username: str) -> dict | None:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return None
    engine = create_engine(database_url, future=True)
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT username, display_name, password_hash, role, photo_url, last_credentials_changed_at "
                "FROM users WHERE username = :username AND is_active = TRUE"
            ),
            {"username": username},
        ).mappings().first()
    return dict(row) if row else None


def authenticate_user(username: str, password: str) -> str:
    if is_login_locked(username):
        raise HTTPException(status_code=429, detail="Trop de tentatives. Réessayez plus tard.")
    if not validate_password_policy(password):
        record_login_failure(username)
        raise HTTPException(status_code=401, detail="Identifiants invalides")

    db_user = get_database_user(username)
    if db_user and verify_password(password, db_user["password_hash"]):
        if is_legacy_password_hash(db_user["password_hash"]):
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                engine = create_engine(database_url, future=True)
                with engine.begin() as conn:
                    conn.execute(
                        text("UPDATE users SET password_hash = :password_hash WHERE username = :username"),
                        {"password_hash": hash_password(password), "username": username},
                    )
        clear_login_failures(username)
        return create_token(username)

    expected = USERS.get(username)
    if expected and secrets.compare_digest(expected, password):
        clear_login_failures(username)
        return create_token(username)

    record_login_failure(username)
    raise HTTPException(status_code=401, detail="Identifiants invalides")


def get_user_profile(username: str) -> dict:
    db_user = get_database_user(username)
    if db_user:
        return {
            "username": db_user["username"],
            "display_name": db_user["display_name"],
            "role": db_user["role"],
            "photo_url": db_user["photo_url"],
            "last_credentials_changed_at": db_user["last_credentials_changed_at"],
        }
    return USER_PROFILES.get(username, {
        "username": username,
        "display_name": username,
        "photo_url": "https://ui-avatars.com/api/?name=%s&background=b60f1e&color=ffffff" % username,
    })


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    token = credentials.credentials
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url, future=True)
        with engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT username, expires_at, revoked_at FROM sessions "
                    "WHERE token = :token"
                ),
                {"token": token},
            ).mappings().first()
            if not row or row["revoked_at"]:
                raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")
            if datetime.utcnow() >= row["expires_at"]:
                conn.execute(
                    text("UPDATE sessions SET revoked_at = :revoked_at WHERE token = :token"),
                    {"revoked_at": datetime.utcnow(), "token": token},
                )
                TOKENS.pop(token, None)
                raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")
            return row["username"]

    session = TOKENS.get(token)
    if not session:
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")
    if datetime.utcnow() >= session["expires_at"]:
        TOKENS.pop(token, None)
        raise HTTPException(status_code=401, detail="Jeton invalide ou expiré")
    return session["username"]


def revoke_token(token: str) -> bool:
    """Revoke a token (remove it from active TOKENS). Returns True if removed."""
    removed = TOKENS.pop(token, None) is not None
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        engine = create_engine(database_url, future=True)
        with engine.begin() as conn:
            result = conn.execute(
                text("UPDATE sessions SET revoked_at = :revoked_at WHERE token = :token AND revoked_at IS NULL"),
                {"revoked_at": datetime.utcnow(), "token": token},
            )
            removed = removed or result.rowcount > 0
    return removed
