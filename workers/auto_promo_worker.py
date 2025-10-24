import threading
import time
import traceback


class AutoPromoWorker(threading.Thread):
    """
    Worker responsável por processar automaticamente tarefas de promoção (AUTO_PROMO).
    """

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        # aliases para o DB (mesmo padrão dos outros workers)
        self.db = app.db_manager
        self.db_manager = app.db_manager
        self._stop_event = threading.Event()

    def run(self):
        """Loop principal adaptado de _process_auto_promo_queue_worker."""
        if getattr(self.app, "is_auto_promo_active", False):
            print("[AutoPromoWorker] Já está ativo.")
            return

        self.app.is_auto_promo_active = True
        print("[AutoPromoWorker] Iniciado.")

        try:
            while not self._stop_event.is_set():
                self.app.auto_promo_worker_event.wait(timeout=30)
                self.app.auto_promo_worker_event.clear()

                tasks = self.db.get_tasks_from_queue(
                    task_type="AUTO_PROMO", status="PENDING", limit=10
                )
                if not tasks:
                    print("[AutoPromoWorker] Nenhuma tarefa pendente.")
                    continue

                for task in tasks:
                    try:
                        task_id = task["task_id"]
                        item_id = task["item_id"]
                        account_nick = task["account_nickname"]

                        self.db.update_task_status(task_id, "PROCESSING", "Ativando promoção...")
                        # Cole aqui a lógica real do seu _process_auto_promo_queue_worker()
                        self._process_auto_promo_task(task)
                        self.db.update_task_status(task_id, "DONE", "Promoção aplicada.")
                    except Exception as e:
                        print(f"[AutoPromoWorker] Erro ao processar item {task.get('item_id')}: {e}")
                        traceback.print_exc()
                        self.db.update_task_status(task.get("task_id"), "ERROR", str(e))
                    time.sleep(1)
        finally:
            self.app.is_auto_promo_active = False
            print("[AutoPromoWorker] Finalizado.")

    def stop(self):
        """Solicita parada do loop."""
        self._stop_event.set()

    def _process_auto_promo_task(self, task):
        """Aqui você vai colar o conteúdo do seu método original _process_auto_promo_queue_worker()."""
        pass
