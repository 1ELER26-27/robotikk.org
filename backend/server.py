"""Private HTTP app for login and invitation activation."""

from __future__ import annotations

import html
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from app import Settings, activate_invitation, authenticate_user, connect_database, find_user_by_id, list_users, record_event


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html><html lang="nb"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(title)} · Robotikk.org</title><link rel="stylesheet" href="/css/style.css"></head><body><main><h1>{html.escape(title)}</h1>{body}</main></body></html>""".encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    settings = Settings.from_environment()

    def send_page(self, status: HTTPStatus, title: str, body: str) -> None:
        payload = page(title, body)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def read_form(self) -> dict[str, str]:
        length = min(int(self.headers.get("Content-Length", "0")), 8192)
        values = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=False)
        return {key: value[0].strip() for key, value in values.items() if value}

    def session_cookie(self, user_id: int) -> str:
        expires = int(time.time()) + 28800
        payload = f"{user_id}.{expires}"
        signature = hmac.new(self.settings.session_secret.encode(), payload.encode(), "sha256").hexdigest()
        return f"{payload}.{signature}"

    def valid_session(self) -> int | None:
        cookie = SimpleCookie(self.headers.get("Cookie", ""))
        value = cookie.get("robotikk_session")
        if value is None:
            return None
        try:
            user_id, expires, signature = value.value.split(".")
            payload = f"{user_id}.{expires}"
            expected = hmac.new(self.settings.session_secret.encode(), payload.encode(), "sha256").hexdigest()
            if int(expires) < int(time.time()) or not hmac.compare_digest(signature, expected):
                return None
            return int(user_id)
        except (ValueError, TypeError):
            return None

    def current_admin(self, connection) -> object | None:
        user_id = self.valid_session()
        if user_id is None:
            return None
        user = find_user_by_id(connection, user_id)
        if user is None or not user["active"] or not user["is_admin"]:
            return None
        return user

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self.send_page(HTTPStatus.OK, "OK", "<p>Backend kjører.</p>")
            return
        if parsed.path == "/logg-inn/":
            self.send_page(HTTPStatus.OK, "Logg inn", '<form method="post"><label>E-post<input type="email" name="email" required autocomplete="email"></label><label>Passord<input type="password" name="password" required autocomplete="current-password"></label><button type="submit">Logg inn</button></form><p><a href="/glemt-passord/">Glemt passord?</a></p>')
            return
        if parsed.path == "/aktiver/":
            token = parse_qs(parsed.query).get("token", [""])[0]
            if not token or len(token) < 20:
                self.send_page(HTTPStatus.BAD_REQUEST, "Ugyldig lenke", "<p>Invitasjonslenken er ugyldig eller utløpt.</p>")
                return
            self.send_page(HTTPStatus.OK, "Aktiver konto", f'<form method="post"><input type="hidden" name="token" value="{html.escape(token)}"><label>Nytt passord<input type="password" name="password" minlength="12" required autocomplete="new-password"></label><button type="submit">Lagre passord</button></form>')
            return
        if parsed.path == "/admin/":
            with connect_database(self.settings.database_path) as connection:
                admin = self.current_admin(connection)
                if admin is None:
                    self.redirect("/logg-inn/")
                    return
                users = list_users(connection)
            rows = "".join(
                "<tr><td data-label=\"Navn\">{}</td><td data-label=\"E-post\">{}</td>"
                "<td data-label=\"Rolle\">{}</td><td data-label=\"Admin\">{}</td>"
                "<td data-label=\"Status\">{}</td></tr>".format(
                    html.escape(row["display_name"]),
                    html.escape(row["email"]),
                    "Lærer" if row["role"] == "laerer" else "Elev",
                    "Ja" if row["is_admin"] else "Nei",
                    "Aktiv" if row["active"] else "Deaktivert",
                )
                for row in users
            )
            body = (
                '<table class="admin-table"><caption>Brukere</caption>'
                "<thead><tr><th scope=\"col\">Navn</th><th scope=\"col\">E-post</th>"
                "<th scope=\"col\">Rolle</th><th scope=\"col\">Admin</th><th scope=\"col\">Status</th></tr></thead>"
                f"<tbody>{rows}</tbody></table>"
            )
            self.send_page(HTTPStatus.OK, "Adminpanel", body)
            return
        self.send_page(HTTPStatus.NOT_FOUND, "Ikke funnet", "<p>Siden finnes ikke.</p>")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/logg-inn/":
            values = self.read_form()
            with connect_database(self.settings.database_path) as connection:
                user = authenticate_user(connection, values.get("email", ""), values.get("password", ""))
                if user is not None:
                    record_event(connection, user["id"], "login")
                    self.send_response(HTTPStatus.SEE_OTHER)
                    self.send_header("Location", "/min-side/")
                    self.send_header("Set-Cookie", f"robotikk_session={self.session_cookie(user['id'])}; Path=/; HttpOnly; Secure; SameSite=Lax; Max-Age=28800")
                    self.end_headers()
                    return
            self.send_page(HTTPStatus.UNAUTHORIZED, "Kunne ikke logge inn", "<p>E-post eller passord er feil.</p>")
            return
        if parsed.path == "/glemt-passord/":
            self.send_page(HTTPStatus.OK, "Sjekk e-posten", "<p>Hvis adressen er registrert, har vi sendt en lenke.</p>")
            return
        if parsed.path == "/aktiver/":
            values = self.read_form()
            token = values.get("token", "")
            password = values.get("password", "")
            if len(password) < 12 or len(token) < 20:
                self.send_page(HTTPStatus.BAD_REQUEST, "Kunne ikke aktivere", "<p>Kontroller feltene og prøv igjen.</p>")
                return
            with connect_database(self.settings.database_path) as connection:
                activated = activate_invitation(connection, token, password)
            if not activated:
                self.send_page(HTTPStatus.BAD_REQUEST, "Kunne ikke aktivere", "<p>Invitasjonslenken er ugyldig eller utløpt.</p>")
                return
            self.send_page(HTTPStatus.OK, "Konto aktivert", "<p>Passordet er lagret. Du kan nå logge inn.</p>")
            return
        self.send_page(HTTPStatus.NOT_FOUND, "Ikke funnet", "<p>Siden finnes ikke.</p>")


def main() -> None:
    host = os.environ.get("ROBOTIKK_BACKEND_HOST", "127.0.0.1")
    port = int(os.environ.get("ROBOTIKK_BACKEND_PORT", "9100"))
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()