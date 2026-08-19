import unittest

from app.main import app


class ApiShapeTests(unittest.TestCase):
    def test_new_routes_exist_and_legacy_routes_are_gone(self):
        paths = {route.path for route in app.routes}
        expected = {
            "/api/v1/profile",
            "/api/v1/today",
            "/api/v1/history",
            "/api/v1/food-templates",
            "/api/v1/met-activities",
            "/api/v1/meals/manual",
            "/api/v1/meals/photo",
            "/api/v1/advice",
            "/api/v1/advice/follow-up",
        }
        self.assertTrue(expected.issubset(paths))
        self.assertNotIn("/api/v1/retrieve", paths)
        self.assertNotIn("/api/v1/chat/stream", paths)
        self.assertNotIn("/api/v1/oss/upload", paths)


if __name__ == "__main__":
    unittest.main()
