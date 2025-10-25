import unittest
import tempfile
import os
from db.manager import DatabaseManager

class DatabaseManagerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.db = DatabaseManager(self.temp_db.name)

    def tearDown(self):
        self.db._get_thread_connection().close()
        os.unlink(self.temp_db.name)

    def test_create_and_fetch_task(self):
        # Inserção direta no banco
        self.db._execute_query(
            "INSERT INTO unified_task_queue (task_type, account_nickname) VALUES (?, ?)",
            ("test_type", "test_user"), commit=True
        )
        results = self.db._execute_query(
            "SELECT * FROM unified_task_queue WHERE account_nickname = ?",
            ("test_user",), fetch_all=True
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["task_type"], "test_type")

    def test_delete_task(self):
        self.db._execute_query(
            "INSERT INTO unified_task_queue (task_type, account_nickname) VALUES (?, ?)",
            ("delete_test", "user2"), commit=True
        )
        task_id = self.db._execute_query(
            "SELECT task_id FROM unified_task_queue WHERE account_nickname = ?",
            ("user2",), fetch_one=True
        )["task_id"]

        self.db._execute_query("DELETE FROM unified_task_queue WHERE task_id = ?", (task_id,), commit=True)
        result = self.db._execute_query("SELECT * FROM unified_task_queue WHERE task_id = ?", (task_id,), fetch_one=True)
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main()
