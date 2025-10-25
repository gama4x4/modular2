from core.scraping import scrape_competitor_info
from services.task_queue import TaskQueueService

class TaskFetcherWorker:
    def __init__(self, db):
        self.queue = TaskQueueService(db)

    def run(self):
        tasks = self.queue.get_pending_tasks(task_type="scrape", limit=10)
        for task in tasks:
            try:
                url = task["payload_json"]
                if url.startswith("{"):
                    import json
                    payload = json.loads(url)
                    url = payload.get("url")

                print(f"Scraping URL: {url}")
                data = scrape_competitor_info(url)

                if data["error"]:
                    raise Exception(data["error"])

                print(f"[{task['task_id']}] Preço: {data['price']}, Estoque: {data['stock']}")
                self.queue.update_task_status(task["task_id"], "COMPLETED", message="Scraping OK", increment_retry=False)

            except Exception as e:
                self.queue.update_task_status(task["task_id"], "FAILED", message=str(e))
