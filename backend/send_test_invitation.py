"""Send one test invitation to the active teacher account."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app import BrevoMailer, Settings, connect_database, create_invitation


def send_test_invitation(settings: Settings) -> None:
    with connect_database(settings.database_path) as connection:
        teachers = connection.execute(
            "SELECT id, email, display_name FROM users WHERE role = 'laerer' AND active = 1 ORDER BY id"
        ).fetchall()
        if len(teachers) != 1:
            raise RuntimeError("Forventet nøyaktig én aktiv lærer for testmail")
        teacher = teachers[0]
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M:%S")
        token = create_invitation(connection, teacher["id"], expires_at)
        link = f"https://robotikk.org/aktiver/?token={token}"
        BrevoMailer(settings).send_invitation(teacher["email"], teacher["display_name"], link)


if __name__ == "__main__":
    send_test_invitation(Settings.from_environment())
    print("Testinvitasjon sendt til aktiv lærer.")