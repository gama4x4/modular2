import json
from datetime import datetime, timedelta

class TaskQueueService:
    def __init__(self, db):
        self.db = db

    def add_task(self, task_type, account_nickname, item_id=None, payload=None, delay_minutes=0):
        payload_json = json.dumps(payload, ensure_ascii=False) if payload else '{}'
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)

        query = """
            INSERT INTO unified_task_queue (
                task_type, account_nickname, item_id, payload_json, scheduled_for
            ) VALUES (?, ?, ?, ?, ?)
        """
        params = (task_type, account_nickname, item_id, payload_json, scheduled_time)
        return self.db._execute_query(query, params, commit=True)

    def get_pending_tasks(self, task_type=None, status='PENDING', limit=10):
        query = "SELECT * FROM unified_task_queue WHERE 1=1"
        params = []

        if task_type:
            query += " AND task_type = ?"
            params.append(task_type)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY added_timestamp ASC LIMIT ?"
        params.append(limit)

        rows = self.db._execute_query(query, tuple(params), fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def update_task_status(self, task_id, new_status, message=None, increment_retry=True):
        set_clause = ["status = ?", "last_error_message = ?"]
        params = [new_status, message]

        if increment_retry:
            set_clause.append("retry_count = retry_count + 1")

        query = f"UPDATE unified_task_queue SET {', '.join(set_clause)} WHERE task_id = ?"
        params.append(task_id)

        self.db._execute_query(query, tuple(params), commit=True)

    def delete_task(self, task_id):
        query = "DELETE FROM unified_task_queue WHERE task_id = ?"
        self.db._execute_query(query, (task_id,), commit=True)

    def clear_all_tasks(self):
        self.db._execute_query("DELETE FROM unified_task_queue", commit=True)
