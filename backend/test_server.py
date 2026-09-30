import hmac
import os
import tempfile
import threading
import time
import unittest
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


if __name__ == "__main__":
    unittest.main()