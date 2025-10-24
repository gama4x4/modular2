import threading
import time
import traceback


class StockDivergenceWorker(threading.Thread):
    """
    Worker responsável por processar tarefas de divergência de estoque (STOCK_DIVERGENCE).
    """

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        # aliases para o DB (mesmo padrão dos outros workers)
        self.db = app.db_manager
        self.db_manager = app.db_manager
        self._stop_event = threading.Event()

    def run(self):
        """Loop principal adaptado de _process_stock_divergence_worker."""
        if getattr(self.app, "is_stock_divergence_active", False):
            print("[StockDivergenceWorker] Já está ativo.")
            return

        self.app.is_stock_divergence_active = True
        print("[StockDivergenceWorker] Iniciado.")

        try:
            while not self._stop_event.is_set():
                self.app.stock_divergence_worker_event.wait(timeout=30)
                self.app.stock_divergence_worker_event.clear()

                tasks = self.db.get_tasks_from_queue(
                    task_type="STOCK_DIVERGENCE", status="PENDING", limit=10
                )
                if not tasks:
                    print("[StockDivergenceWorker] Fila vazia.")
                    continue

                for task in tasks:
                    try:
                        task_id = task["task_id"]
                        item_id = task["item_id"]
                        account_nick = task["account_nickname"]
                        self.db.update_task_status(task_id, "PROCESSING", "Verificando estoque...")

                        # Cole aqui a lógica real de verificação individual
                        self._process_stock_check(task)

                        self.db.update_task_status(task_id, "DONE", "Verificação concluída.")
                    except Exception as e:
                        print(f"[StockDivergenceWorker] Erro no item {task.get('item_id')}: {e}")
                        traceback.print_exc()
                        self.db.update_task_status(task.get("task_id"), "ERROR", str(e))
                    time.sleep(0.5)
        finally:
            self.app.is_stock_divergence_active = False
            print("[StockDivergenceWorker] Finalizado.")

    def stop(self):
        """Solicita parada do loop."""
        self._stop_event.set()

    def _process_stock_check(self, task):
        """Lógica individual (cole aqui o conteúdo de _get_stock_diff_for_item ou equivalente)."""
        pass
