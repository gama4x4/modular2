import json
from services.task_queue import TaskQueueService
from integrations.mercadolivre_api import make_ml_api_request

class AutoPromoWorker:
    def __init__(self, db):
        self.queue = TaskQueueService(db)

    def run(self):
        tasks = self.queue.get_pending_tasks(task_type="auto_promo", limit=10)
        for task in tasks:
            try:
                payload = json.loads(task["payload_json"])
                access_token = payload["access_token"]
                item_id = payload["item_id"]
                competitor_price = float(payload.get("competitor_price", 0))
                adjustment = float(payload.get("adjustment", -1.0))  # desconto automático de R$1 por padrão

                # Obtem dados do anúncio atual
                url = f"https://api.mercadolibre.com/items/{item_id}"
                item_data = make_ml_api_request(url, access_token)

                current_price = float(item_data["price"])
                new_price = max(1.0, competitor_price + adjustment)

                if new_price < current_price:
                    # Aplica novo preço via API
                    update_url = f"https://api.mercadolibre.com/items/{item_id}"
                    resp = make_ml_api_request(update_url, access_token, params={"price": new_price})

                    print(f"[{item_id}] Preço alterado: de {current_price} → {new_price}")
                    self.queue.update_task_status(task["task_id"], "COMPLETED", message="Preço ajustado", increment_retry=False)
                else:
                    print(f"[{item_id}] Preço não alterado. Valor já competitivo.")
                    self.queue.update_task_status(task["task_id"], "SKIPPED", message="Preço já competitivo", increment_retry=False)

            except Exception as e:
                print(f"Erro ao processar tarefa {task['task_id']}: {e}")
                self.queue.update_task_status(task["task_id"], "FAILED", message=str(e))
