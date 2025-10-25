import os
import platform

# Diretório padrão de dados
APP_DATA_DIR = os.path.join(os.path.expanduser("~"), ".ml_tiny_app_data_v2")

# Nome do arquivo do banco de dados
DB_NAME = "ml_app.db"
DB_PATH_FINAL = os.path.join(APP_DATA_DIR, DB_NAME)

# Constantes visuais e fontes
UI_SCALE = 1.3
BASE_FONT_FAMILY = "Segoe UI" if platform.system() == "Windows" else "Arial"

# Diretórios auxiliares (imagens, exportações, logs)
EXPORT_DIR = os.path.join(APP_DATA_DIR, "exports")
LOG_DIR = os.path.join(APP_DATA_DIR, "logs")
CACHE_DIR = os.path.join(APP_DATA_DIR, "cache")

# Cria os diretórios automaticamente se não existirem
for path in [APP_DATA_DIR, EXPORT_DIR, LOG_DIR, CACHE_DIR]:
    os.makedirs(path, exist_ok=True)
