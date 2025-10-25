# Sistema Modular - Mercado Livre + Tiny ERP

Este é um projeto modular Python para gerenciamento de tarefas, integração com a API do Mercado Livre e Tiny ERP, e uma interface gráfica simples com Tkinter.

## 📦 Estrutura Modular

```
core/
    scraping.py          # Funções de scraping de dados do Mercado Livre
    text_utils.py        # Funções de limpeza e normalização de texto
db/
    manager.py           # Gerenciador SQLite com controle de tarefas
services/
    task_queue.py        # Serviço de fila de tarefas
integrations/
    mercadolivre_api.py  # Integração OAuth e API Mercado Livre
    tiny_api.py          # Integração com a API do Tiny ERP
app_gui/
    queue_manager.py     # GUI para visualização e controle de tarefas
main.py                  # Ponto de entrada da aplicação
requirements.txt         # Dependências do projeto
```

## 🚀 Como usar

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Rode o app:
```bash
python main.py
```

## 🛠 Tecnologias

- Python 3.8+
- SQLite3
- Tkinter (GUI)
- Requests (API)
- BeautifulSoup + lxml (Scraping)

## 📄 Licença

MIT
