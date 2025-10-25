import sys
import tkinter as tk
from db.manager import DatabaseManager
from services.task_queue import TaskQueueService

# Exemplo de GUI básica com botão para listar tarefas
class MainApplication(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.queue_service = TaskQueueService(self.db)

        self.title("Sistema Modular - ML + Tiny ERP")
        self.geometry("400x300")

        tk.Button(self, text="Listar Tarefas", command=self.listar_tarefas).pack(pady=20)
        self.output = tk.Text(self, height=10)
        self.output.pack(fill="both", expand=True)

    def listar_tarefas(self):
        self.output.delete("1.0", tk.END)
        tasks = self.queue_service.get_pending_tasks()
        for task in tasks:
            self.output.insert(tk.END, f"{task['task_id']}: {task['task_type']} - {task['status']}\n")

def main():
    try:
        db = DatabaseManager()
        app = MainApplication(db)
        app.mainloop()
    except Exception as e:
        print(f"Erro fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
