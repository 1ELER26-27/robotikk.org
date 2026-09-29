import os
import unittest

os.environ.setdefault("ROBOTIKK_SESSION_SECRET", "test-secret")

from server import page


class ServerTests(unittest.TestCase):
    def test_page_escapes_user_visible_title(self):
        result = page("<test>", "<p>ok</p>").decode("utf-8")
        self.assertIn("&lt;test&gt;", result)
        self.assertNotIn("<title><test>", result)


if __name__ == "__main__":
    unittest.main()