"""Grant or revoke admin rights for an existing teacher user."""

from __future__ import annotations

import sys

from app import Settings, connect_database, set_user_admin


def main() -> None:
    if len(sys.argv) != 3 or sys.argv[2] not in {"true", "false"}:
        raise SystemExit("Bruk: python3 backend/set_admin.py <e-post> <true|false>")
    email = sys.argv[1]
    is_admin = sys.argv[2] == "true"
    settings = Settings.from_environment()
    with connect_database(settings.database_path) as connection:
        if not set_user_admin(connection, email, is_admin):
            raise SystemExit("Fant ikke brukeren, eller brukeren er ikke en lærer")
    print(f"Admintilgang for {email}: {'på' if is_admin else 'av'}.")


if __name__ == "__main__":
    main()
