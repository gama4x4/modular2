import json
from services.task_queue import TaskQueueService
from integrations.mercadolivre_api import make_ml_api_request

class BulkEditorWorker:
    def __init__(self, db):
        self.queue = TaskQueueService(db)

    def run(self):
        tasks = self.queue.get_pending_tasks(task_type="bulk_edit", limit=10)
        for task in tasks:
            try:
                payload = json.loads(task["payload_json"])
                access_token = payload["access_token"]
                item_id = payload["item_id"]
                updates = payload.get("updates", {})  # Exemplo: {"title": "Novo Título", "available_quantity": 10}

                update_url = f"https://api.mercadolibre.com/items/{item_id}"
                headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

                import requests
                response = requests.put(update_url, headers=headers, json=updates)
                response.raise_for_status()

                print(f"[{item_id}] Atualizado com sucesso.")
                self.queue.update_task_status(task["task_id"], "COMPLETED", message="Atualização OK", increment_retry=False)

            except Exception as e:
                print(f"[{task['task_id']}] Erro na atualização: {e}")
                self.queue.update_task_status(task["task_id"], "FAILED", message=str(e))
