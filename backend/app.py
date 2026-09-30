"""Small standard-library backend foundation.

The public Hugo catalogue remains static. This package owns private runtime
data and will later serve authenticated student and teacher workflows.
"""

from __future__ import annotations

import hashlib
import html
import hmac
import json
import os
import secrets
import sqlite3
import urllib.request
import urllib.error
from datetime import datetime, timezone
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
    is_admin INTEGER NOT NULL DEFAULT 0 CHECK (is_admin IN (0, 1)),
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
    _migrate_schema(connection)
    return connection


def _migrate_schema(connection: sqlite3.Connection) -> None:
    """Add columns to tables created before they existed in SCHEMA."""
    columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
    if "is_admin" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        connection.commit()


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


def create_invitation(connection: sqlite3.Connection, user_id: int, expires_at: str) -> str:
    token, token_hash = new_invitation_token()
    connection.execute(
        "INSERT INTO invitation_tokens (user_id, token_hash, expires_at) VALUES (?, ?, ?)",
        (user_id, token_hash, expires_at),
    )
    connection.commit()
    return token


def find_user_by_email(connection: sqlite3.Connection, email: str) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE lower(email) = lower(?)", (email.strip(),)).fetchone()


def find_user_by_id(connection: sqlite3.Connection, user_id: int) -> sqlite3.Row | None:
    return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def list_users(connection: sqlite3.Connection) -> list[sqlite3.Row]:
    return connection.execute(
        "SELECT id, email, display_name, role, active, is_admin FROM users ORDER BY role, display_name"
    ).fetchall()


def set_user_admin(connection: sqlite3.Connection, email: str, is_admin: bool) -> bool:
    """Grant or revoke admin rights. Only teachers ('laerer') may be admins."""
    row = find_user_by_email(connection, email)
    if row is None or (is_admin and row["role"] != "laerer"):
        return False
    connection.execute("UPDATE users SET is_admin = ? WHERE id = ?", (int(is_admin), row["id"]))
    connection.commit()
    return True


def set_user_password(connection: sqlite3.Connection, user_id: int, password: str) -> None:
    connection.execute("UPDATE users SET password_hash = ?, active = 1 WHERE id = ?", (hash_password(password), user_id))
    connection.execute(
        "UPDATE invitation_tokens SET used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND used_at IS NULL",
        (user_id,),
    )
    connection.commit()


def activate_invitation(connection: sqlite3.Connection, token: str, password: str) -> bool:
    row = connection.execute(
        "SELECT user_id FROM invitation_tokens WHERE token_hash = ? AND used_at IS NULL AND expires_at > CURRENT_TIMESTAMP",
        (hash_token(token),),
    ).fetchone()
    if row is None:
        return False
    set_user_password(connection, row["user_id"], password)
    return True


def authenticate_user(connection: sqlite3.Connection, email: str, password: str) -> sqlite3.Row | None:
    row = find_user_by_email(connection, email)
    if row is None or not row["active"] or not row["password_hash"]:
        return None
    return row if verify_password(password, row["password_hash"]) else None


def record_event(connection: sqlite3.Connection, actor_user_id: int | None, event_type: str) -> None:
    connection.execute("INSERT INTO audit_events (actor_user_id, event_type) VALUES (?, ?)", (actor_user_id, event_type))
    connection.commit()


class BrevoMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_invitation(self, recipient: str, display_name: str, link: str) -> None:
        if not self.settings.brevo_api_key:
            raise RuntimeError("BREVO_API_KEY mangler")
        payload = {
            "sender": {"name": self.settings.brevo_sender_name, "email": self.settings.brevo_sender_email},
            "to": [{"email": recipient, "name": display_name}],
            "subject": "Invitasjon til Robotikk.org",
            "htmlContent": (
                "<p>Du er invitert til Robotikk.org.</p>"
                "<p><a href=\"{}\">Aktiver kontoen din</a>. Lenken er tidsbegrenset.</p>"
            ).format(html.escape(link, quote=True)),
        }
        request = urllib.request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=json.dumps(payload).encode("utf-8"),
            headers={"accept": "application/json", "api-key": self.settings.brevo_api_key, "content-type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                pass
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Brevo avviste e-posten (HTTP {error.code}): {detail}") from error


def healthcheck(settings: Settings) -> dict[str, str]:
    with connect_database(settings.database_path) as connection:
        connection.execute("SELECT 1").fetchone()
    return {"status": "ok", "brevo": "configured" if settings.brevo_api_key else "not-configured"}