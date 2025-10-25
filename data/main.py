from db.manager import DatabaseManager
from app_gui.queue_window import UnifiedQueueManagerWindow
from core.config import DB_PATH_FINAL

if __name__ == "__main__":
    db = DatabaseManager(DB_PATH_FINAL)
    app = UnifiedQueueManagerWindow(db)
    app.mainloop()
