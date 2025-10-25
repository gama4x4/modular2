import tkinter as tk
from tkinter import ttk
from db.manager import DatabaseManager
from services.task_queue import TaskQueueService
from app_gui.widgets import create_green_button
from app_gui.utils import autoscale_fonts_by_screen

class UnifiedQueueManagerWindow(tk.Tk):
    def __init__(self, db: DatabaseManager):
        super().__init__()
        self.title("Gerenciador de Fila de Tarefas")
        self.geometry("1000x600")
        autoscale_fonts_by_screen(self)

        self.db = db
        self.queue = TaskQueueService(self.db)

        self.create_widgets()
        self.refresh_queue_table()

    def create_widgets(self):
        self.tree = ttk.Treeview(self, columns=("ID", "Tipo", "Conta", "Status", "Retries"), show="headings")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=5)

        create_green_button(btn_frame, "Recarregar", self.refresh_queue_table).pack(side="left", padx=5)
        create_green_button(btn_frame, "Fechar", self.destroy).pack(side="left", padx=5)

    def refresh_queue_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        tasks = self.queue.get_pending_tasks()
        for task in tasks:
            self.tree.insert("", "end", values=(
                task["task_id"], task["task_type"],
                task["account_nickname"], task["status"],
                task["retry_count"]
            ))
