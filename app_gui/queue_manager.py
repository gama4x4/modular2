import tkinter as tk
from tkinter import ttk, messagebox
from services.task_queue import TaskQueueService

class QueueManagerWindow(tk.Toplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.db = db
        self.queue_service = TaskQueueService(self.db)
        self.title("Gerenciador de Fila de Tarefas")
        self.geometry("600x400")
        self.build_widgets()
        self.refresh_tasks()

    def build_widgets(self):
        self.tree = ttk.Treeview(self, columns=("task_type", "account", "status", "retry"), show="headings")
        self.tree.heading("task_type", text="Tipo de Tarefa")
        self.tree.heading("account", text="Conta")
        self.tree.heading("status", text="Status")
        self.tree.heading("retry", text="Tentativas")

        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Atualizar", command=self.refresh_tasks).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Apagar Selecionada", command=self.delete_selected_task).pack(side=tk.LEFT, padx=5)

    def refresh_tasks(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        tasks = self.queue_service.get_pending_tasks(limit=50)
        for task in tasks:
            self.tree.insert("", tk.END, iid=task["task_id"], values=(
                task["task_type"],
                task["account_nickname"],
                task["status"],
                task["retry_count"]
            ))

    def delete_selected_task(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Atenção", "Selecione uma tarefa para apagar.")
            return

        task_id = selected[0]
        confirm = messagebox.askyesno("Confirmação", f"Apagar tarefa {task_id}?")
        if confirm:
            self.queue_service.delete_task(task_id)
            self.refresh_tasks()
