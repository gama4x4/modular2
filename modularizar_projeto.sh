#!/bin/bash
echo 'Criando estrutura de pastas e arquivos...'
mkdir -p core
touch core/scraping.py
touch core/text_utils.py
mkdir -p utils
touch utils/constants.py
touch utils/paths.py
mkdir -p app_gui
touch app_gui/main_window.py
touch app_gui/queue_manager.py
mkdir -p integrations
touch integrations/mercadolivre_api.py
touch integrations/tiny_api.py
touch integrations/oauth_handlers.py
mkdir -p services
touch services/task_queue.py
touch services/promotions.py
mkdir -p workers
touch workers/bulk_editor.py
touch workers/auto_promo.py
touch workers/fetcher.py
mkdir -p db
touch db/manager.py
touch db/migrations.py
mkdir -p assets
touch main.py
touch requirements.txt
touch README.md
echo 'Estrutura criada com sucesso.'