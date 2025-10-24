# app_gui/tabs/tab_tiny_products.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Esta aba depende de componentes já existentes no seu projeto:
# - App._open_abc_import_dialog()   → abre o diálogo de Curva ABC
# - App._trigger_stock_divergence_processing()
# - App._trigger_auto_promo_processing()

class TabTinyProducts(ttk.Frame):
    """
    Aba 12 — Produtos da Tiny
    Centraliza ações de catálogo do Tiny.
    """
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._build_ui()

    def _build_ui(self):
        # Cabeçalho
        header = ttk.Frame(self, padding=(12, 12, 12, 6))
        header.pack(fill="x")
        ttk.Label(
            header, text="Produtos da Tiny", font=("Segoe UI", 14, "bold")
        ).pack(side="left")

        # Barra de ações principais
        actions = ttk.Frame(self, padding=(12, 6, 12, 6))
        actions.pack(fill="x")

        # 1) Importar Curva ABC (dentro da aba, como solicitado)
        ttk.Button(
            actions,
            text="Importar Curva ABC...",
            style="Accent.TButton",
            command=self._on_import_abc_clicked,
        ).pack(side="left", padx=(0, 8))

        # 2) Verificar Divergência de Estoque (sinaliza o worker)
        ttk.Button(
            actions,
            text="Verificar Divergência de Estoque",
            command=self._on_check_stock_divergence_clicked,
        ).pack(side="left", padx=4)

        # 3) Auto Promo (sinaliza o worker)
        ttk.Button(
            actions,
            text="Rodar Auto Promo",
            command=self._on_auto_promo_clicked,
        ).pack(side="left", padx=4)

        # Separador
        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=(8, 8))

        # Área central (placeholder de tabela/lista de produtos)
        center = ttk.Frame(self, padding=12)
        center.pack(fill="both", expand=True)

        ttk.Label(
            center,
            text=(
                "Aqui você pode listar/filtrar produtos do Tiny, exibir métricas de ABC, "
                "e acionar rotinas específicas."
            ),
            wraplength=900,
            justify="left",
        ).pack(anchor="w")

        # Rodapé
        footer = ttk.Frame(self, padding=(12, 0, 12, 12))
        footer.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(footer, textvariable=self.status_var).pack(side="left")

    # -------------------------------
    # Handlers / callbacks da UI
    # -------------------------------
    def _on_import_abc_clicked(self):
        """
        Abre o diálogo de Curva ABC e, se confirmado, chama o fluxo que você já tem.
        """
        try:
            self.app._open_abc_import_dialog()
            self.status_var.set("Importação de Curva ABC concluída (ou cancelada).")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao importar Curva ABC:\n{e}", parent=self)
            self.status_var.set("Erro ao importar Curva ABC.")

    def _on_check_stock_divergence_clicked(self):
        """
        Apenas sinaliza o worker. A lógica de enfileirar tarefas deve estar no seu fluxo.
        """
        try:
            self.app._trigger_stock_divergence_processing()
            self.status_var.set("Sinal enviado ao worker de divergência de estoque.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao sinalizar verificação de estoque:\n{e}", parent=self)

    def _on_auto_promo_clicked(self):
        """
        Apenas sinaliza o worker. A lógica de criação das tasks AUTO_PROMO deve estar no seu fluxo.
        """
        try:
            self.app._trigger_auto_promo_processing()
            self.status_var.set("Sinal enviado ao worker de Auto Promo.")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao sinalizar Auto Promo:\n{e}", parent=self)
