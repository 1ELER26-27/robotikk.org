"""Import an approved local user CSV into the private SQLite database."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from app import Settings, connect_database


REQUIRED_COLUMNS = {"email", "display_name", "role", "active", "github_username"}


def import_users(csv_path: Path, settings: Settings) -> int:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError("CSV må ha kolonnene email, display_name, role, active, github_username")

        imported = 0
        with connect_database(settings.database_path) as connection:
            for row in reader:
                raw_email = (row.get("email") or "").strip()
                raw_display_name = (row.get("display_name") or "").strip()
                raw_role = (row.get("role") or "").strip()
                raw_active = (row.get("active") or "").strip()
                raw_github_username = (row.get("github_username") or "").strip()
                if not any((raw_email, raw_display_name, raw_role, raw_active, raw_github_username)):
                    continue
                email = raw_email.lower()
                display_name = raw_display_name
                role = raw_role.lower().replace("æ", "ae")
                active = raw_active.lower() == "true"
                github_username = raw_github_username or None
                if not email or not display_name or role not in {"elev", "laerer"}:
                    raise ValueError("Hver rad må ha e-post, navn og rolle elev/laerer")
                connection.execute(
                    """INSERT INTO users (email, display_name, role, github_username, active)
                       VALUES (?, ?, ?, ?, ?)
                       ON CONFLICT(email) DO UPDATE SET display_name=excluded.display_name,
                         role=excluded.role, github_username=excluded.github_username,
                         active=excluded.active""",
                    (email, display_name, role, github_username, int(active)),
                )
                imported += 1
            connection.commit()
    return imported


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Bruk: python3 backend/import_users.py /sti/til/invited-users.csv")
    settings = Settings.from_environment()
    print(f"Importerte {import_users(Path(sys.argv[1]), settings)} brukere.")