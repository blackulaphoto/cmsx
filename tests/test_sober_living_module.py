import os
import unittest
from tempfile import TemporaryDirectory
from pathlib import Path


class SoberLivingStoreTest(unittest.TestCase):
    def setUp(self):
        os.environ.pop("DATABASE_URL", None)

        import backend.modules.sober_living.database as sober_db

        self.sober_db = sober_db
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.original_sqlite_path = sober_db.SQLITE_PATH
        self.original_store_instance = sober_db._store_instance
        sober_db.SQLITE_PATH = Path(self.temp_dir.name) / "sober_living_ops.db"
        sober_db._store_instance = None

    def tearDown(self):
        self.sober_db.SQLITE_PATH = self.original_sqlite_path
        self.sober_db._store_instance = self.original_store_instance

    def test_inactive_house_serializes_false_and_is_excluded_from_active_list(self):
        store = self.sober_db.get_store()
        house = store.create_house({"house_name": "Inactive Regression House", "total_beds": 1})

        with self.sober_db._db() as conn:
            self.sober_db._exec(
                conn,
                "UPDATE sober_living_houses SET is_active = %s WHERE house_id = %s",
                ("0", house["house_id"]),
            )

        detail = store.get_house(house["house_id"])
        self.assertFalse(detail["is_active"])
        self.assertFalse(any(h["house_id"] == house["house_id"] for h in store.list_houses()))

    def test_update_house_converts_active_flag_before_persisting(self):
        store = self.sober_db.get_store()
        house = store.create_house({"house_name": "Active Flag Update House", "total_beds": 1})

        updated = store.update_house(house["house_id"], {"is_active": "false"})

        self.assertFalse(updated["is_active"])
        self.assertFalse(any(h["house_id"] == house["house_id"] for h in store.list_houses()))


if __name__ == "__main__":
    unittest.main()
