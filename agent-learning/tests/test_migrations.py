import unittest
from pathlib import Path


MIGRATION_DIR = Path(__file__).resolve().parents[1] / "db" / "migrations"


class MigrationSafetyTests(unittest.TestCase):
    def test_migrations_do_not_drop_legacy_application_tables(self):
        sql = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(MIGRATION_DIR.glob("*.sql"))
        ).upper()

        for table in (
            "CHECKPOINT_WRITES",
            "CHECKPOINT_BLOBS",
            "CHECKPOINTS",
            "CHECKPOINT_MIGRATIONS",
        ):
            self.assertNotIn(f"DROP TABLE IF EXISTS {table}", sql)


if __name__ == "__main__":
    unittest.main()
