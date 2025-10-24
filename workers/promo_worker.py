import threading
import time
import json
import traceback


class PromoWorker(threading.Thread):
    """
    Worker responsável por processar tarefas de promoção (AUTO_PROMO e PROMO_ACTIVATION).
    """

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        # aliases para o DB (compatível com o restante do projeto)
        self.db = app.db_manager
        self.db_manager = app.db_manager
        self._stop_event = threading.Event()

    def run(self):
        """Loop principal, adaptado de _process_auto_promo_queue_worker."""
        if getattr(self.app, "is_promo_worker_active", False):
            print("[PromoWorker] Já está ativo.")
            return

        self.app.is_promo_worker_active = True
        print("[PromoWorker] Iniciado.")

        try:
            while not self._stop_event.is_set():
                self.app.auto_promo_worker_event.wait(timeout=30)
                self.app.auto_promo_worker_event.clear()

                tasks = self.db.get_tasks_from_queue(
                    task_type="AUTO_PROMO", status="PENDING", limit=5
                )
                if not tasks:
                    continue

                for task in tasks:
                    try:
                        task_id = task["task_id"]
                        item_id = task["item_id"]
                        account_nick = task["account_nickname"]
                        self.db.update_task_status(task_id, "PROCESSING", "Ativando promoção...")

                        # Aqui você vai colar o conteúdo real de _process_auto_promo_queue_worker()
                        self._process_promo_task(task)

                        self.db.update_task_status(task_id, "DONE", "Concluído.")
                    except Exception as e:
                        print(f"[PromoWorker] Erro no item {task.get('item_id')}: {e}")
                        traceback.print_exc()
                        self.db.update_task_status(task.get("task_id"), "ERROR", str(e))
                    time.sleep(1)
        finally:
            self.app.is_promo_worker_active = False
            print("[PromoWorker] Finalizado.")

    def stop(self):
        """Solicita parada do loop."""
        self._stop_event.set()

    def _process_promo_task(self, task):
        """Lógica real do AUTO_PROMO/PROMO_ACTIVATION — cole aqui depois o conteúdo do seu método original."""
        pass
