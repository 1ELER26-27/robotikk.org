"""Small standard-library backend foundation.

The public Hugo catalogue remains static. This package owns private runtime
data and will later serve authenticated student and teacher workflows.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from dataclasses import dataclass
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('elev', 'laerer')),
    github_username TEXT,
    password_hash TEXT,
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS invitation_tokens (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TEXT NOT NULL,
    used_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY,
    actor_user_id INTEGER REFERENCES users(id),
    event_type TEXT NOT NULL,
    target_type TEXT,
    target_id TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass(frozen=True)
class Settings:
    database_path: Path
    brevo_api_key: str | None
    brevo_sender_email: str
    brevo_sender_name: str
    session_secret: str

    @classmethod
    def from_environment(cls) -> "Settings":
        database_path = Path(os.environ.get("ROBOTIKK_DATABASE", "backend/data/robotikk.sqlite3"))
        session_secret = os.environ.get("ROBOTIKK_SESSION_SECRET")
        if not session_secret:
            raise RuntimeError("ROBOTIKK_SESSION_SECRET mangler")
        return cls(
            database_path=database_path,
            brevo_api_key=os.environ.get("BREVO_API_KEY"),
            brevo_sender_email=os.environ.get("BREVO_SENDER_EMAIL", "noreply@login.robotikk.org"),
            brevo_sender_name=os.environ.get("BREVO_SENDER_NAME", "Robotikk.org"),
            session_secret=session_secret,
        )


def connect_database(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(SCHEMA)
    return connection


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Passordet må ha minst 12 tegn")
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=2**14, r=8, p=1)
    return "scrypt$16384$8$1${}${}".format(salt.hex(), digest.hex())


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
        )
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_invitation_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def healthcheck(settings: Settings) -> dict[str, str]:
    with connect_database(settings.database_path) as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok", "brevo": "configured" if settings.brevo_api_key else "not-configured"}