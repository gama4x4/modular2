from db.manager import DatabaseManager
from workers.fetcher import TaskFetcherWorker
from workers.auto_promo import AutoPromoWorker
from workers.bulk_editor import BulkEditorWorker

def run_all_workers():
    db = DatabaseManager()

    print("🔍 Rodando Worker: FETCHER")
    TaskFetcherWorker(db).run()

    print("💰 Rodando Worker: AUTO PROMO")
    AutoPromoWorker(db).run()

    print("🛠️  Rodando Worker: BULK EDITOR")
    BulkEditorWorker(db).run()

if __name__ == "__main__":
    run_all_workers()
