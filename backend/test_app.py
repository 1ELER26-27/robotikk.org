import os
import tempfile
import unittest
from pathlib import Path

from app import Settings, activate_invitation, connect_database, create_invitation, hash_password, healthcheck, new_invitation_token, verify_password


class BackendFoundationTests(unittest.TestCase):
    def test_password_hash_is_salted_and_verifiable(self):
        encoded = hash_password("correct horse battery staple")
        self.assertNotEqual(encoded, hash_password("correct horse battery staple"))
        self.assertTrue(verify_password("correct horse battery staple", encoded))
        self.assertFalse(verify_password("wrong password", encoded))

    def test_short_password_is_rejected(self):
        with self.assertRaises(ValueError):
            hash_password("too short")

    def test_invitation_token_is_not_stored_in_plaintext(self):
        token, token_hash = new_invitation_token()
        self.assertNotEqual(token, token_hash)
        self.assertEqual(len(token_hash), 64)

    def test_database_schema_and_healthcheck(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robotikk.sqlite3"
            settings = Settings(path, None, "noreply@example.invalid", "Example", "test-secret")
            result = healthcheck(settings)
            self.assertEqual(result["status"], "ok")
            with connect_database(path) as connection:
                tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
            self.assertTrue({"users", "invitation_tokens", "audit_events"}.issubset(tables))

    def test_invitation_can_activate_user_once(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robotikk.sqlite3"
            connection = connect_database(path)
            cursor = connection.execute("INSERT INTO users (email, display_name, role) VALUES (?, ?, ?)", ("student@example.invalid", "Example", "elev"))
            token = create_invitation(connection, cursor.lastrowid, "2999-01-01 00:00:00")
            self.assertTrue(activate_invitation(connection, token, "correct horse battery staple"))
            self.assertFalse(activate_invitation(connection, token, "another password here"))


if __name__ == "__main__":
    unittest.main()