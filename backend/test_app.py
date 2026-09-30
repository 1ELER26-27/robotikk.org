import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import Settings, activate_invitation, connect_database, create_invitation, hash_password, healthcheck, new_invitation_token, set_user_admin, verify_password
from import_users import import_users


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

    def test_user_import_accepts_display_roles_and_blank_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "users.csv"
            csv_path.write_text(
                "email,display_name,role,active,github_username\n"
                "student@example.invalid,Elev,Elev,true,\n"
                "teacher@example.invalid,Lærer,Lærer,true,\n\n",
                encoding="utf-8",
            )
            database_path = Path(directory) / "robotikk.sqlite3"
            settings = Settings(database_path, None, "noreply@example.invalid", "Example", "test-secret")
            self.assertEqual(import_users(csv_path, settings), 2)
            with connect_database(database_path) as connection:
                roles = {row["role"] for row in connection.execute("SELECT role FROM users")}
            self.assertEqual(roles, {"elev", "laerer"})

    def test_only_teachers_can_become_admin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robotikk.sqlite3"
            connection = connect_database(path)
            connection.execute("INSERT INTO users (email, display_name, role) VALUES (?, ?, ?)", ("student@example.invalid", "Example", "elev"))
            connection.execute("INSERT INTO users (email, display_name, role) VALUES (?, ?, ?)", ("teacher@example.invalid", "Example", "laerer"))
            connection.commit()
            self.assertFalse(set_user_admin(connection, "student@example.invalid", True))
            self.assertTrue(set_user_admin(connection, "teacher@example.invalid", True))
            row = connection.execute("SELECT is_admin FROM users WHERE email = ?", ("teacher@example.invalid",)).fetchone()
            self.assertEqual(row["is_admin"], 1)
            self.assertTrue(set_user_admin(connection, "teacher@example.invalid", False))

    def test_migration_adds_is_admin_column_to_old_database(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "robotikk.sqlite3"
            legacy_connection = sqlite3.connect(path)
            legacy_connection.execute(
                """CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL CHECK (role IN ('elev', 'laerer')),
                    github_username TEXT,
                    password_hash TEXT,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            legacy_connection.commit()
            legacy_connection.close()
            with connect_database(path) as connection:
                columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)")}
            self.assertIn("is_admin", columns)


if __name__ == "__main__":
    unittest.main()