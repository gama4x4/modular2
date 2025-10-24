import threading
import time
import json
import traceback


class PriceCheckWorker(threading.Thread):
    """
    Worker responsável pela fila PRICE_CHECK.
    Processa automaticamente tarefas de verificação de preço.
    """

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        # aliases para o DB (mesmo padrão do BulkWorker)
        self.db = app.db_manager
        self.db_manager = app.db_manager
        self._stop_event = threading.Event()

    def run(self):
        """Loop principal adaptado de _process_price_check_queue_worker."""
        if getattr(self.app, "is_price_check_worker_active", False):
            print("[PriceCheckWorker] Já está ativo.")
            return

        self.app.is_price_check_worker_active = True
        print("[PriceCheckWorker] Iniciado.")
        try:
            while not self._stop_event.is_set():
                # espera sinal externo (botão/cron) com timeout
                self.app.price_check_worker_event.wait(timeout=60)
                self.app.price_check_worker_event.clear()

                tasks = self.db.get_tasks_from_queue(
                    task_type="PRICE_CHECK", status="PENDING", limit=10
                )
                if not tasks:
                    print("[PriceCheckWorker] Fila vazia.")
                    continue

                for task in tasks:
                    try:
                        task_id = task["task_id"]
                        item_id = task["item_id"]
                        account_nick = task["account_nickname"]

                        self.db.update_task_status(task_id, "PROCESSING", "Verificando...")
                        self._process_single_price_check(task)  # <- cole a lógica real aqui
                        self.db.update_task_status(task_id, "DONE", "Concluído.")
                    except Exception as e:
                        print(f"[PriceCheckWorker] Erro no item {task.get('item_id')}: {e}")
                        traceback.print_exc()
                        self.db.update_task_status(task.get("task_id"), "ERROR", str(e))
                    time.sleep(0.5)
        finally:
            self.app.is_price_check_worker_active = False
            print("[PriceCheckWorker] Finalizado.")

    def stop(self):
        """Solicita parada do loop."""
        self._stop_event.set()

    def _process_single_price_check(self, task):
        """
        Lógica individual de verificação — cole aqui o conteúdo do seu
        '_bulk_price_check_worker' (ou o trecho que calcula/verifica preço
        para um item) adaptado para receber 'task' como dict.
        """
        pass
