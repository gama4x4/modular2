import os
import sys
import sqlite3
import threading
from datetime import datetime
from tkinter import messagebox

class DatabaseManager:
    def __init__(self, db_path=None):
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        db_filename = 'app_data.db'
        final_db_path = os.path.join(base_dir, db_filename)
        self.db_name = final_db_path if db_path is None else db_path

        self.thread_local = threading.local()
        try:
            os.makedirs(os.path.dirname(self.db_name), exist_ok=True)
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            self._create_tables_with_cursor(cursor)
            conn.commit()
            conn.close()
            print(f"DatabaseManager initialized. DB Path: {self.db_name}")
        except sqlite3.Error as e:
            critical_msg = f"CRITICAL DATABASE ERROR: {e}\nPath: {self.db_name}"
            print(critical_msg)
            messagebox.showerror("Erro Fatal no Banco de Dados", critical_msg)
            sys.exit(1)

    def _create_tables_with_cursor(self, cursor):
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS unified_task_queue (
            task_id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_type TEXT NOT NULL,
            account_nickname TEXT,
            item_id TEXT,
            payload_json TEXT,
            status TEXT DEFAULT 'PENDING',
            retry_count INTEGER DEFAULT 0,
            last_error_message TEXT,
            scheduled_for TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            added_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

    def _get_thread_connection(self):
        if not hasattr(self.thread_local, "connection"):
            conn = sqlite3.connect(self.db_name, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode=WAL;")
            self.thread_local.connection = conn
        return self.thread_local.connection

    def _execute_query(self, query, params=(), fetch_one=False, fetch_all=False, commit=False):
        conn = self._get_thread_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            if commit:
                conn.commit()
            if fetch_one:
                return cursor.fetchone()
            if fetch_all:
                return cursor.fetchall()
            return cursor
        except sqlite3.Error as e:
            print(f"Database Error: {e}\nQuery: {query}")
            return None
