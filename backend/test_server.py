import hmac
import json
import os
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("ROBOTIKK_SESSION_SECRET", "test-secret")
os.environ.setdefault("ROBOTIKK_DATABASE", str(Path(tempfile.mkdtemp()) / "robotikk.sqlite3"))

from app import connect_database
from server import Handler, page


class ServerTests(unittest.TestCase):
    def test_page_escapes_user_visible_title(self):
        result = page("<test>", "<p>ok</p>").decode("utf-8")
        self.assertIn("&lt;test&gt;", result)
        self.assertNotIn("<title><test>", result)


class AdminRouteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with connect_database(Handler.settings.database_path) as connection:
            admin_cursor = connection.execute(
                "INSERT INTO users (email, display_name, role, active, is_admin) VALUES (?, ?, 'laerer', 1, 1)",
                ("admin@example.invalid", "Admin"),
            )
            student_cursor = connection.execute(
                "INSERT INTO users (email, display_name, role, active) VALUES (?, ?, 'elev', 1)",
                ("student@example.invalid", "Elev Eksempel"),
            )
            connection.commit()
            cls.admin_id = admin_cursor.lastrowid
            cls.student_id = student_cursor.lastrowid
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.thread.join()

    def _session_cookie(self, user_id: int) -> str:
        expires = int(time.time()) + 3600
        payload = f"{user_id}.{expires}"
        signature = hmac.new(Handler.settings.session_secret.encode(), payload.encode(), "sha256").hexdigest()
        return f"{payload}.{signature}"

    def _get(self, path: str, user_id: int | None = None) -> tuple[str, str]:
        headers = {}
        if user_id is not None:
            headers["Cookie"] = f"robotikk_session={self._session_cookie(user_id)}"
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", headers=headers)
        with urllib.request.urlopen(request) as response:
            return response.geturl(), response.read().decode("utf-8")

    def _status(self, path: str, user_id: int | None = None) -> int:
        headers = {}
        if user_id is not None:
            headers["Cookie"] = f"robotikk_session={self._session_cookie(user_id)}"
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", headers=headers)
        try:
            with urllib.request.urlopen(request) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code

    def _post(self, path: str, data: dict, user_id: int | None = None) -> tuple[str, int, str]:
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if user_id is not None:
            headers["Cookie"] = f"robotikk_session={self._session_cookie(user_id)}"
        body = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request) as response:
                return response.geturl(), response.status, response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            return error.geturl(), error.code, error.read().decode("utf-8")

    def test_admin_route_redirects_anonymous_visitors_to_login(self):
        final_url, _ = self._get("/admin/")
        self.assertTrue(final_url.endswith("/logg-inn/"))

    def test_admin_route_redirects_non_admin_users_to_login(self):
        final_url, _ = self._get("/admin/", user_id=self.student_id)
        self.assertTrue(final_url.endswith("/logg-inn/"))

    def test_admin_route_lists_users_for_admin(self):
        final_url, body = self._get("/admin/", user_id=self.admin_id)
        self.assertTrue(final_url.endswith("/admin/"))
        self.assertIn("Adminpanel", body)
        self.assertIn("Elev Eksempel", body)
        self.assertIn("student@example.invalid", body)

    def test_min_side_redirects_anonymous_visitors_to_login(self):
        final_url, _ = self._get("/min-side/")
        self.assertTrue(final_url.endswith("/logg-inn/"))

    def test_min_side_shows_admin_link_for_admin(self):
        final_url, body = self._get("/min-side/", user_id=self.admin_id)
        self.assertTrue(final_url.endswith("/min-side/"))
        self.assertIn("Admin", body)
        self.assertIn("/admin/", body)

    def test_min_side_hides_admin_link_for_non_admin(self):
        final_url, body = self._get("/min-side/", user_id=self.student_id)
        self.assertTrue(final_url.endswith("/min-side/"))
        self.assertIn("Elev Eksempel", body)
        self.assertNotIn("/admin/", body)

    def test_internal_auth_check_rejects_anonymous_visitors(self):
        self.assertEqual(self._status("/internal/auth-check"), 401)

    def test_internal_auth_check_accepts_any_active_user(self):
        self.assertEqual(self._status("/internal/auth-check", user_id=self.student_id), 200)
        self.assertEqual(self._status("/internal/auth-check", user_id=self.admin_id), 200)

    def test_api_me_rejects_anonymous_visitors(self):
        self.assertEqual(self._status("/api/me"), 401)

    def test_api_me_reports_role_and_admin_flag(self):
        _, body = self._get("/api/me", user_id=self.admin_id)
        payload = json.loads(body)
        self.assertTrue(payload["is_admin"])
        self.assertEqual(payload["role"], "laerer")

    def test_non_admin_cannot_create_or_delete_users(self):
        final_url, _, _ = self._post(
            "/admin/ny-bruker/",
            {"email": "annen@example.invalid", "display_name": "Annen", "role": "elev"},
            user_id=self.student_id,
        )
        self.assertTrue(final_url.endswith("/logg-inn/"))

    def test_admin_can_add_and_then_delete_a_user(self):
        _, status, body = self._post(
            "/admin/ny-bruker/",
            {"email": "ny@example.invalid", "display_name": "Ny Bruker", "role": "elev"},
            user_id=self.admin_id,
        )
        self.assertEqual(status, 200)
        self.assertIn("aktiver/?token=", body)
        with connect_database(Handler.settings.database_path) as connection:
            new_user = connection.execute("SELECT id FROM users WHERE email = ?", ("ny@example.invalid",)).fetchone()
        self.assertIsNotNone(new_user)

        _, confirm_body = self._get(f"/admin/slett-bruker/?id={new_user['id']}", user_id=self.admin_id)
        self.assertIn("Slette", confirm_body)

        final_url, _, _ = self._post("/admin/slett-bruker/", {"id": str(new_user["id"])}, user_id=self.admin_id)
        self.assertTrue(final_url.endswith("/admin/"))
        with connect_database(Handler.settings.database_path) as connection:
            gone = connection.execute("SELECT id FROM users WHERE email = ?", ("ny@example.invalid",)).fetchone()
        self.assertIsNone(gone)

    def test_admin_cannot_delete_self(self):
        final_url, _, _ = self._post("/admin/slett-bruker/", {"id": str(self.admin_id)}, user_id=self.admin_id)
        self.assertTrue(final_url.endswith("/admin/"))
        with connect_database(Handler.settings.database_path) as connection:
            still_here = connection.execute("SELECT id FROM users WHERE id = ?", (self.admin_id,)).fetchone()
        self.assertIsNotNone(still_here)


if __name__ == "__main__":
    unittest.main()