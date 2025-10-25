import unittest
import tempfile
import os
from db.manager import DatabaseManager
from services.task_queue import TaskQueueService

class TaskQueueTestCase(unittest.TestCase):
    def setUp(self):
        # cria banco em memória temporária
        self.db_file = tempfile.NamedTemporaryFile(delete=False)
        self.db = DatabaseManager(self.db_file.name)
        self.queue = TaskQueueService(self.db)

    def tearDown(self):
        self.db._get_thread_connection().close()
        os.unlink(self.db_file.name)

    def test_add_and_retrieve_task(self):
        self.queue.add_task("test", "acc1", "123", {"url": "http://example.com"})
        tasks = self.queue.get_pending_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['task_type'], "test")

    def test_update_status(self):
        self.queue.add_task("test", "acc1")
        task = self.queue.get_pending_tasks()[0]
        self.queue.update_task_status(task["task_id"], "DONE", "OK", increment_retry=False)
        updated = self.queue.get_pending_tasks(status="DONE")[0]
        self.assertEqual(updated['status'], "DONE")
        self.assertEqual(updated['last_error_message'], "OK")

if __name__ == '__main__':
    unittest.main()
