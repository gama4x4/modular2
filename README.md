# Modular2 🧠🔧

Este projeto é a versão **modularizada** do antigo script `MERCADOLIVRE_TINY_API_3.0.py`.  
Transformamos um monólito em um sistema escalável, testável e pronto para produção.

---

## 🚀 Como executar

```bash
git clone https://github.com/gama4x4/modular2
cd modular2
pip install -r requirements.txt
python main.py
```

---

## 🧱 Estrutura Modular

```
core/
  └── config.py, text_utils.py
db/
  └── manager.py
services/
  └── task_queue.py, ...
integrations/
  └── mercadolivre_api.py, tiny_api.py, oauth_handler.py
app_gui/
  └── queue_window.py, widgets.py, utils.py
scraping/
  └── category_browser.py
tests/
  └── test_*.py
main.py
```

---

## 🧪 Testes

```bash
python -m unittest discover -s tests
```

---

## 📦 Dependências (requirements.txt)

- requests
- pandas
- beautifulsoup4
- lxml
- tkinter
- pillow
- reportlab (opcional)

---

## 🛠️ Feito com 💚 por [@gama4x4](https://github.com/gama4x4)
