import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from datetime import datetime

class UnifiedQueueManagerWindow(tk.Toplevel):
    def __init__(self, master, app_instance):
        super().__init__(master)
        self.app = app_instance
        self.db = self.app.db_manager
        self.title("Gerenciador de Fila Unificado")
        self.geometry("1100x700")
        self.focus_set()

        self.task_type_filter_var = tk.StringVar(value="Todos")
        # <<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO (1/3) >>>>>>>>>>>>>>>>>>>>>>
        # 1. Adiciona a variável para o novo filtro de STATUS, com o padrão "Todos"
        self.status_filter_var = tk.StringVar(value="Todos")
        # <<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO (1/3) >>>>>>>>>>>>>>>>>>>>>>>>

        self.TASK_TYPE_DISPLAY_MAP = {
            "Todos": "Todos",
            "BULK_EDIT": "Edição em Massa",
            "PROMO_VERIFICATION": "Verificação de Margem de Promo",
            "PROMO_ACTIVATION": "Ativação de Promoção (Manual)",
            "AUTO_PROMO": "Ativação de Promoção (Automática)",
            "PRICE_CHECK": "Verificação de Preço",
            "AD_FETCH": "Busca de Anúncios (Contas)",
            "AD_REPROCESS": "Rebusca de Anúncio (Falhas)",
            "TECH_SPECS_SCAN": "Scan Ficha Técnica",
            "TECH_SPECS_PATCH": "Aplicar Ficha Técnica"
        }
        
        # <<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO (2/3) >>>>>>>>>>>>>>>>>>>>>>
        # 2. Cria um mapa para os status, para usar na UI e na busca no DB
        self.STATUS_FILTER_MAP = {
            "Todos": None, # Usará None para não filtrar por status no DB
            "Pendentes": "PENDING",
            "Com Erro": "ERROR",
            "Concluídos": "DONE",
            "Processando": "PROCESSING"
        }
        # <<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO (2/3) >>>>>>>>>>>>>>>>>>>>>>>>

        self._setup_ui()
        self._populate_queue_tree()


    def _setup_ui(self):
        main_frame = ttk.Frame(self, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        top_frame = ttk.Frame(main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(top_frame, text="Filtrar por Tipo:").pack(side=tk.LEFT, padx=(0, 5))
        
        type_combo = ttk.Combobox(top_frame, textvariable=self.task_type_filter_var, 
                                  values=list(self.TASK_TYPE_DISPLAY_MAP.values()), 
                                  state="readonly")
        type_combo.pack(side=tk.LEFT, padx=5)
        type_combo.bind("<<ComboboxSelected>>", self._populate_queue_tree)

        # <<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO (INTERFACE) >>>>>>>>>>>>>>>>>>>>>>
        # Adiciona o Combobox de filtro de STATUS na interface
        ttk.Label(top_frame, text="Filtrar por Status:").pack(side=tk.LEFT, padx=(10, 5))
        status_combo = ttk.Combobox(top_frame, textvariable=self.status_filter_var,
                                  values=list(self.STATUS_FILTER_MAP.keys()),
                                  state="readonly")
        status_combo.pack(side=tk.LEFT, padx=5)
        status_combo.bind("<<ComboboxSelected>>", self._populate_queue_tree)
        # <<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO (INTERFACE) >>>>>>>>>>>>>>>>>>>>>>>>
        
        ttk.Button(top_frame, text="Gerar Relatório de Erros", command=self._generate_error_report).pack(side=tk.RIGHT, padx=5)
        
        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        cols = ("id", "type", "status", "retries", "item_id", "account", "details", "error")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="extended")
        
        self.tree.heading("id", text="ID"); self.tree.column("id", width=50, stretch=False)
        self.tree.heading("type", text="Tipo Tarefa"); self.tree.column("type", width=150)
        self.tree.heading("status", text="Status"); self.tree.column("status", width=90, anchor="center")
        self.tree.heading("retries", text="Tent."); self.tree.column("retries", width=40, anchor="center")
        self.tree.heading("item_id", text="Alvo (ID)"); self.tree.column("item_id", width=120)
        self.tree.heading("account", text="Conta"); self.tree.column("account", width=120)
        self.tree.heading("details", text="Detalhes"); self.tree.column("details", width=150)
        self.tree.heading("error", text="Último Erro/Resultado"); self.tree.column("error", width=300)
        
        self.tree.tag_configure('ERROR', background='#FFCDD2')
        self.tree.tag_configure('PENDING', background='#FFF9C4')
        self.tree.tag_configure('PROCESSING', background='#C5E1A5')
        self.tree.tag_configure('DONE', background='#E8F5E9')

        ysb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ysb.set, xscrollcommand=xsb.set)
        
        ysb.pack(side=tk.RIGHT, fill=tk.Y); xsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        action_frame = ttk.Frame(main_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(action_frame, text="Processar Fila Pendente Agora", command=self._process_all_now, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Processar Selecionados", command=self._process_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Resetar Falhas", command=self._reset_failed).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Remover Selecionados", command=self._clear_selected).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Limpar TODA a Fila", command=self._clear_all).pack(side=tk.LEFT, padx=15)
        ttk.Frame(action_frame).pack(side=tk.LEFT, fill=tk.X, expand=True) 
        ttk.Button(action_frame, text="Atualizar", command=self._populate_queue_tree).pack(side=tk.RIGHT)

    # --- INÍCIO DOS NOVOS MÉTODOS PARA O RELATÓRIO ---
    def _generate_error_report(self):
        """Busca todas as tarefas com erro e exibe em uma nova janela de relatório."""
        self.update_idletasks()
        self.config(cursor="watch")
        
        # Busca todas as tarefas com erro, sem limite de quantidade
        error_tasks = self.db.get_tasks_from_queue(status='ERROR', limit=None)
        
        self.config(cursor="")

        if not error_tasks:
            messagebox.showinfo("Relatório de Erros", "Nenhuma tarefa com erro encontrada na fila.", parent=self)
            return

        # Formata o texto do relatório
        report_lines = [f"Relatório de Erros da Fila - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", "="*80]
        for task in error_tasks:
            task_type_display = self.TASK_TYPE_DISPLAY_MAP.get(task['task_type'], task['task_type'])
            report_lines.append(f"ID Tarefa: {task['task_id']}")
            report_lines.append(f"Tipo: {task_type_display}")
            report_lines.append(f"Alvo: {task.get('item_id') or 'N/A'}")
            report_lines.append(f"Conta: {task.get('account_nickname') or 'N/A'}")
            report_lines.append(f"Tentativas: {task.get('retry_count', 0)}")
            report_lines.append(f"Mensagem de Erro: {task.get('last_error_message', 'Nenhuma mensagem.')}")
            report_lines.append("-" * 80)
        
        report_text = "\n".join(report_lines)
        
        # Exibe a janela de relatório
        self._show_report_window(report_text)

    # DENTRO DA CLASSE UnifiedQueueManagerWindow
    # SUBSTITUA ESTE MÉTODO INTEIRO

    def _show_report_window(self, report_text):
        """Cria e exibe a janela de Toplevel com o relatório."""
        report_win = tk.Toplevel(self)
        report_win.title("Relatório de Tarefas com Erro")
        report_win.geometry("800x600")
        report_win.transient(self)
        report_win.grab_set()

        main_frame = ttk.Frame(report_win, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # <<<<<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>
        # Acessa a fonte através da instância principal da aplicação (self.app)
        text_area = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, font=self.app.scrolledtext_font)
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>
        
        text_area.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        text_area.insert(tk.END, report_text)
        text_area.config(state=tk.DISABLED)

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Salvar em Arquivo...", command=lambda: self._save_report_to_file(report_text)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Fechar", command=report_win.destroy).pack(side=tk.RIGHT, padx=5)

    def _save_report_to_file(self, report_text):
        """Abre um diálogo para salvar o relatório em um arquivo de texto."""
        filepath = filedialog.asksaveasfilename(
            parent=self,
            title="Salvar Relatório de Erros",
            defaultextension=".txt",
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")],
            initialfile=f"relatorio_erros_fila_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        )
        if not filepath:
            return

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_text)
            messagebox.showinfo("Sucesso", f"Relatório salvo em:\n{filepath}", parent=self)
        except Exception as e:
            messagebox.showerror("Erro ao Salvar", f"Não foi possível salvar o arquivo:\n{e}", parent=self)
    # --- FIM DOS NOVOS MÉTODOS ---

    def _populate_queue_tree(self, event=None):
        self.tree.delete(*self.tree.get_children())
        
        # Lê e traduz o filtro de TIPO
        filter_display_type = self.task_type_filter_var.get()
        filter_internal_type = next((k for k, v in self.TASK_TYPE_DISPLAY_MAP.items() if v == filter_display_type), None)
        if filter_internal_type == "Todos":
            filter_internal_type = None

        # Lê e traduz o filtro de STATUS
        filter_display_status = self.status_filter_var.get()
        filter_internal_status = self.STATUS_FILTER_MAP.get(filter_display_status)
        
        # Busca no banco de dados com os filtros corretos e sem limite
        items = self.db.get_tasks_from_queue(
            task_type=filter_internal_type,
            status=filter_internal_status,
            limit=None 
        )
        
        for item in items:
            tags = (item['status'],)
            task_type_display = self.TASK_TYPE_DISPLAY_MAP.get(item['task_type'], item['task_type'])
            details_display = ""
            try:
                payload = json.loads(item.get('payload_json') or '{}')
                if item['task_type'] == 'AUTO_PROMO':
                    details_display = f"Desconto: {payload.get('desired_discount_percent', 0.0):.2f}%"
                elif item['task_type'] == 'PROMO_ACTIVATION':
                    details_display = f"Promo ID: {payload.get('promotion_id')}"
                elif item['task_type'] == 'TECH_SPECS_PATCH':
                     new_attrs = payload.get('new_attributes', {})
                     details_display = f"{len(new_attrs)} atributo(s)"
            except (json.JSONDecodeError, TypeError):
                details_display = "Payload Inválido"

            self.tree.insert("", "end", iid=item['task_id'], values=(
                item['task_id'], task_type_display, item['status'], item.get('retry_count', 0),
                item.get('item_id') or "N/A", item.get('account_nickname') or "N/A",
                details_display, (item.get('last_error_message') or "")[:150]
            ), tags=tags)
        self.title(f"Gerenciador de Fila Unificado ({len(items)} tarefas)")

    def _process_all_now(self):
        messagebox.showinfo("Ação", "Sinalizando todos os workers para processarem suas filas pendentes.", parent=self)
        self.app.ad_fetch_worker_event.set()
        self.app.price_check_worker_event.set()
        self.app.auto_promo_worker_event.set()
        
        # <<<<<<<<<<<<<<<<<<<< LINHA DE CORREÇÃO ADICIONADA AQUI >>>>>>>>>>>>>>>>>>>>
        if hasattr(self.app, 'stock_divergence_worker_event'):
            self.app.stock_divergence_worker_event.set()
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>>>>
            
        # Os workers de edição e promo manual são iniciados sob demanda
        self.destroy()

    def _process_selected(self):
        selected_iids = self.tree.selection()
        if not selected_iids:
            messagebox.showinfo("Ação", "Nenhuma tarefa selecionada.", parent=self)
            return
        
        task_ids = [int(iid) for iid in selected_iids]
        tasks = self.db.get_tasks_from_queue(task_ids=task_ids)
        if not tasks:
            messagebox.showerror("Erro", "Tarefas selecionadas não encontradas no banco de dados.", parent=self)
            return

        # Separa as tarefas por tipo para chamar os workers corretos
        tasks_by_type = {}
        for task in tasks:
            task_type = task['task_type']
            if task_type not in tasks_by_type:
                tasks_by_type[task_type] = []
            tasks_by_type[task_type].append(task['task_id'])

        for task_type, ids in tasks_by_type.items():
            if task_type == 'BULK_EDIT':
                self.app._start_bulk_worker_from_ui(ids)
            elif task_type == 'PROMO_ACTIVATION':
                self.app._start_promo_worker_from_ui(ids)
            else:
                # Para workers que rodam em loop, apenas sinalizamos
                worker_event = getattr(self.app, f"{task_type.lower()}_worker_event", None)
                if worker_event:
                    worker_event.set()

        messagebox.showinfo("Ação", "As tarefas selecionadas foram enviadas para processamento.", parent=self)
        self.destroy()

    def _reset_failed(self):
        selected_iids = self.tree.selection()
        task_ids_to_reset = []
        if selected_iids:
            task_ids_to_reset = [int(iid) for iid in selected_iids]
        else: # Se nada selecionado, reseta todos com erro
            all_tasks = self.db.get_tasks_from_queue(status='ERROR')
            task_ids_to_reset = [t['task_id'] for t in all_tasks]

        if not task_ids_to_reset:
            messagebox.showinfo("Ação", "Nenhuma tarefa com erro encontrada para resetar.", parent=self)
            return

        if messagebox.askyesno("Confirmar", f"Resetar {len(task_ids_to_reset)} tarefa(s) com erro para o status 'PENDING'?", parent=self):
            updated_count = self.db.reset_tasks_by_ids(task_ids_to_reset)
            messagebox.showinfo("Sucesso", f"{updated_count} tarefa(s) foram resetadas.", parent=self)
            self._populate_queue_tree()

    def _clear_selected(self):
        selected_iids = self.tree.selection()
        if not selected_iids: return
        if messagebox.askyesno("Confirmar", f"Remover {len(selected_iids)} tarefa(s) da fila permanentemente?", parent=self):
            task_ids = [int(iid) for iid in selected_iids]
            self.db.delete_tasks_from_queue(task_ids)
            self._populate_queue_tree()

    def _clear_all(self):
        if messagebox.askyesno("Confirmar", "Limpar TODAS as tarefas de TODAS as filas permanentemente?\nEsta ação não pode ser desfeita.", icon='warning', parent=self):
            self.db.clear_all_tasks_from_queue()
            self._populate_queue_tree()
