import tkinter as tk
import queue  # no topo do arquivo ou aqui mesmo
from tkinter import ttk, messagebox

# === Importações locais (mantêm o código modular) ===
from core.database_manager import DatabaseManager
from app_gui.queue_manager_window import UnifiedQueueManagerWindow
from app_gui.abc_dialogs import ABCCurveImportDialog
from workers.bulk_worker import BulkWorker
from workers.price_check_worker import PriceCheckWorker
from workers.promo_worker import PromoWorker
from workers.stock_divergence_worker import StockDivergenceWorker
from workers.auto_promo_worker import AutoPromoWorker
from app_gui.tabs.tab_tiny_products import TabTinyProducts
from services.abc_importer import ABCImporter
from services.abc_service import ABCService
from services.task_enqueue import TaskEnqueueService, EnqueueItem
from core.scraping import scrape_ml_product_basic_info
from core.text_utils import html_to_text



class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ML Tiny V4 Modular")
        self.root.geometry("1400x900")
        self.root.minsize(1200, 800)

        # === Inicializações Globais ===
        self.db_manager = DatabaseManager()
        self.db = self.db_manager  # alias opcional, evita AttributeError em trechos antigos
        self._init_worker_events()
        # === Fila e flags da Aba 8 ===
        self.bulk_edit_action_queue = queue.Queue()
        self.is_bulk_processing_active = False
        self.fixed_prices = {}                 # usado pelo BulkWorker (preço fixo por SKU)
        self.update_qty_sync_tiny_var = False  # se ainda não existir como BooleanVar na UI
        # === Configuração da Interface ===
        self._setup_ui()

    # -------------------------------------------------
    # Eventos e Workers
    # -------------------------------------------------
    def _init_worker_events(self):
        """Cria os eventos (threads placeholders) dos workers."""
        import threading
        self.bulk_worker_event = threading.Event()
        self.price_check_worker_event = threading.Event()
        self.promo_worker_event = threading.Event()
        self.stock_divergence_worker_event = threading.Event()
        self.auto_promo_worker_event = threading.Event()

        # Instâncias dos workers (placeholder)
        self.bulk_worker = BulkWorker(self)
        self.price_check_worker = PriceCheckWorker(self)
        self.promo_worker = PromoWorker(self)
        self.stock_divergence_worker = StockDivergenceWorker(self)
        self.auto_promo_worker = AutoPromoWorker(self)

    # -------------------------------------------------
    # Interface Principal
    # -------------------------------------------------
    def _setup_ui(self):
        """Configura as abas principais e menus."""

        # === Menus principais (criar antes do Notebook) ===
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Gerenciar Fila", command=self._open_queue_manager)
        file_menu.add_separator()
        file_menu.add_command(label="Sair", command=self.root.quit)
        menubar.add_cascade(label="Ferramentas", menu=file_menu)

        # === Abas (depois do menu) ===
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.tab_bulk = ttk.Frame(notebook)
        self.tab_catalog = ttk.Frame(notebook)
        self.tab_quality = ttk.Frame(notebook)
        self.tab_tiny_products = TabTinyProducts(notebook, self)  # ✅ nova aba

        notebook.add(self.tab_bulk, text="Aba 8 - Edição em Massa")
        notebook.add(self.tab_catalog, text="Aba 17 - Catálogo")
        notebook.add(self.tab_quality, text="Aba 18 - Qualidade / Ficha Técnica")
        notebook.add(self.tab_tiny_products, text="Aba 12 - Produtos da Tiny")


    def _start_bulk_worker_from_ui(self, task_ids_to_process: list):
        """
        [CORRIGIDO V-FINAL] Inicia o worker de edição em massa com uma lista específica de task_ids do DB.
        A correção principal é NÃO usar json.loads aqui, passando a string JSON diretamente para a fila.
        """
        if not task_ids_to_process:
            print("Worker UI Trigger: Nenhum ID de tarefa fornecido.")
            return

        if not self.bulk_edit_action_queue.empty():
            messagebox.showwarning("Processamento", "O worker já está processando outra leva de itens. Aguarde a finalização.", parent=self.root)
            return

        tasks_from_db = self.db_manager.get_bulk_queue_items_by_ids(task_ids_to_process)
        if not tasks_from_db:
            messagebox.showerror("Erro", "Não foi possível encontrar as tarefas selecionadas no banco de dados.", parent=self.root)
            return
        
        enqueued_count = 0
        for task_data in tasks_from_db:
            try:
                # --- AQUI ESTÁ A CORREÇÃO ---
                # Os dados 'actions_payload_json' e 'original_item_data_json'
                # são passados como strings para a fila, que é o formato que o worker espera.
                # Removemos as chamadas json.loads() que estavam causando o erro.
                task_tuple = (
                    task_data['task_id'],
                    task_data['account_nickname'],
                    task_data['item_id'],
                    task_data['actions_payload_json'],      # <-- DADO É STRING (CORRETO)
                    task_data['original_item_data_json']   # <-- DADO É STRING (CORRETO)
                )
                self.bulk_edit_action_queue.put(task_tuple)
                self.db_manager.update_bulk_queue_item_status(task_data['task_id'], 'QUEUED')
                enqueued_count += 1
            except (KeyError) as e:
                print(f"Erro ao preparar tarefa ID {task_data.get('task_id')} da DB para a fila: {e}")
                self.db_manager.update_bulk_queue_item_status(task_data.get('task_id'), 'ERROR', f"Erro de formato no DB: {e}")

        if enqueued_count > 0:
            if hasattr(self, 'bulk_edit_ads_status_label'):
                self.bulk_edit_ads_status_label.config(text=f"{enqueued_count} tarefas enfileiradas para processamento...")
            # ✅ dispara o worker novo (classe BulkWorker) pelo evento
            self._trigger_bulk_edit_processing()
        else:
            if hasattr(self, 'bulk_edit_ads_status_label'):
                self.bulk_edit_ads_status_label.config(text="Nenhuma tarefa válida para processar.")



    def _ensure_thread_started(self, thread_attr_name):
        """
        Garante que o worker foi startado. Se ainda não, inicia.
        Retorna a instância do worker.
        """
        worker = getattr(self, thread_attr_name, None)
        if worker is None:
            raise RuntimeError(f"Worker '{thread_attr_name}' não foi criado em _init_worker_events().")
        if not worker.is_alive():
            try:
                worker.start()
            except RuntimeError:
                # Se já foi startado e terminou, recria e starta de novo
                cls = worker.__class__
                new_worker = cls(self)
                setattr(self, thread_attr_name, new_worker)
                new_worker.start()
                return new_worker
        return worker

    def _trigger_bulk_edit_processing(self):
        """Sinaliza o worker da Aba 8 (BULK_EDIT)."""
        self._ensure_thread_started("bulk_worker")
        self.bulk_edit_worker_event.set()

    def _trigger_price_check_processing(self):
        """Sinaliza o worker de PRICE_CHECK."""
        self._ensure_thread_started("price_check_worker")
        self.price_check_worker_event.set()

    def _trigger_auto_promo_processing(self):
        """Sinaliza o worker de AUTO_PROMO."""
        self._ensure_thread_started("auto_promo_worker")
        self.auto_promo_worker_event.set()

    def _trigger_promo_activation_processing(self):
        """Se você separar PROMO_ACTIVATION do AUTO_PROMO, sinalize aqui um event específico."""
        self._ensure_thread_started("promo_worker")
        self.promo_worker_event.set()

    def _trigger_stock_divergence_processing(self):
        """Sinaliza o worker de divergência de estoque."""
        self._ensure_thread_started("stock_divergence_worker")
        self.stock_divergence_worker_event.set()


    def _tiny_api_v3_request(self, method, endpoint, params=None, json_data=None, expect_binary=False):
        access_token = self._get_tiny_v3_access_token()
        if not access_token:
            print("Erro API Tiny v3: Não autenticado.")
            return None

        headers = {'Authorization': f'Bearer {access_token}', 'User-Agent': APP_USER_AGENT}
        if json_data:
            headers['Content-Type'] = 'application/json'
        
        url = f"{TINY_V3_API_BASE_URL}{endpoint}"
        
        max_retries = 3 
        for attempt in range(max_retries):
            try:
                response = requests.request(
                    method=method.upper(), url=url, headers=headers,
                    params=params, json=json_data, timeout=25
                )

                if response.status_code == 429: # Rate Limit
                    if attempt < max_retries - 1:
                        retry_after_header = response.headers.get('Retry-After')
                        wait_time = int(retry_after_header) if retry_after_header and retry_after_header.isdigit() else 2 ** (attempt + 1)
                        print(f"Tiny API Rate Limit (429). Tentativa {attempt + 1}/{max_retries}. Aguardando {wait_time}s...")
                        if hasattr(self, 'tiny_products_status_label'):
                            self.root.after(0, lambda w=wait_time: self.tiny_products_status_label.config(text=f"Rate Limit API Tiny. Aguardando {w}s..."))
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"Tiny API Rate Limit (429) persistente após {max_retries} tentativas. Abortando.")
                        response.raise_for_status()
                
                # Trata 404 silenciosamente (produto sem imagem é esperado)
                if response.status_code == 404:
                    print(f"API Tiny v3: Recurso não encontrado (404) para endpoint '{endpoint}'. Retornando None.")
                    return None
                
                response.raise_for_status()
                
                if expect_binary:
                    return response.content
                
                if response.status_code == 204:
                    return {"status_code": 204, "success": True}

                return response.json() if response.content else {"status_code": response.status_code, "success": True}

    # <<<<<<< INÍCIO DO BLOCO DE CÓDIGO CORRIGIDO >>>>>>>>>
            except requests.exceptions.HTTPError as e_http:
                print(f"Erro HTTP na API v3 do Tiny: {e_http.response.status_code} para {url}")
                if e_http.response and e_http.response.text:
                    print(f"  Detalhe do Erro (Tiny API): {e_http.response.text[:500]}")
                if e_http.response.status_code == 429 and attempt < max_retries - 1:
                    continue
                # TENTA RETORNAR O ERRO EM JSON PARA EXIBIÇÃO NA UI
                try:
                    return e_http.response.json()
                except json.JSONDecodeError:
                    return {"error": "HTTP Error", "status_code": e_http.response.status_code, "details": e_http.response.text[:500]}
            except requests.exceptions.RequestException as e_req:
                print(f"Falha de conexão com a API v3 do Tiny (Tentativa {attempt + 1}): {url}\n{e_req}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    # Retorna um erro estruturado
                    return {"error": "Connection Error", "details": str(e_req)}
            except Exception as e_gen:
                print(f"Erro inesperado com a API v3 Tiny: {e_gen}")
                # Retorna um erro estruturado
                return {"error": "Unexpected Error", "details": str(e_gen)}
    # <<<<<<<<<<< FIM DO BLOCO DE CÓDIGO CORRIGIDO >>>>>>>>>>>
        
        return None

    def _get_tiny_available_stock_v3(self, tiny_product_id_v3: str, sum_reserves_if_true: bool = False) -> float | None:
        """
        [VERSÃO CORRIGIDA E FINAL V2] Busca o saldo de um produto na Tiny API v3.
        - Se o ID for de um produto PAI com UMA variação, busca o estoque da variação.
        - Se for um PAI com MÚLTIPLAS variações, retorna erro (ambiguidade).
        - Se for um produto SIMPLES ou uma VARIAÇÃO, busca o estoque diretamente.
        """
        log_prefix = f"TinyGetStockV3 (ID: {tiny_product_id_v3}): "
        print(f"{log_prefix}Iniciando busca de estoque.")

        if not tiny_product_id_v3:
            return None

        # 1. Busca os detalhes completos do produto para verificar se é pai, incluindo as variações.
        product_details = self._tiny_api_v3_request('GET', f'/produtos/{tiny_product_id_v3}', params={'incluir': 'variacoes'})
        
        if not product_details or not product_details.get("id"):
            print(f"{log_prefix}FALHA ao obter detalhes do produto. Atualização cancelada.")
            return None

        variations = product_details.get("variacoes", [])
        target_id_for_stock = tiny_product_id_v3

        # 2. Lógica de decisão: Pai, Filho ou Simples?
        if isinstance(variations, list) and variations:
            if len(variations) == 1:
                # É um pai com uma única variação. O estoque está na variação.
                target_id_for_stock = str(variations[0].get("id"))
                print(f"{log_prefix}Produto pai com 1 variação. Redirecionando busca de estoque para o ID do filho: {target_id_for_stock}")
            else:
                # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
                # <<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>>
                # É um pai com múltiplas variações. O estoque é ambíguo. Retornamos None em vez de gerar um erro.
                error_msg = f"SKU de produto pai com {len(variations)} variações. Estoque ambíguo."
                print(f"{log_prefix}AVISO: {error_msg}. Retornando estoque como None.")
                return None # <-- ESTA É A LINHA CORRIGIDA
                # <<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>>>
                # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
        
        # 3. Busca de Estoque para o ID Alvo
        deposito_id_para_usar_int = None
        try:
            deposito_id_config_str = str(self.app_config.get('tiny_v3_default_deposito_id', '')).strip()
            if deposito_id_config_str.isdigit():
                deposito_id_para_usar_int = int(deposito_id_config_str)
            else:
                new_deposito_id = simpledialog.askstring(
                    "ID Depósito Padrão Tiny API v3", "Insira o ID numérico do seu Depósito Padrão no Tiny ERP:", parent=self.root
                )
                if new_deposito_id and new_deposito_id.strip().isdigit():
                    deposito_id_para_usar_int = int(new_deposito_id.strip())
                    self.app_config['tiny_v3_default_deposito_id'] = str(deposito_id_para_usar_int)
                    self.db_manager.set_app_config_value('tiny_v3_default_deposito_id', str(deposito_id_para_usar_int))
                else:
                    messagebox.showerror("Configuração Necessária", "O ID do Depósito Padrão é necessário para obter o estoque correto.", parent=self.root)
                    return None
        except Exception as e:
            print(f"{log_prefix}Erro ao obter ID do depósito: {e}")
            return None

        estoque_resp = self._tiny_api_v3_request('GET', f'/estoque/{target_id_for_stock}')

        if not estoque_resp or not isinstance(estoque_resp, dict) or not isinstance(estoque_resp.get("depositos"), list):
            print(f"{log_prefix}Falha ao obter detalhes de estoque da API (resposta ou lista de depósitos inválida) para o ID alvo {target_id_for_stock}.")
            return None

        deposito_alvo = next((d for d in estoque_resp["depositos"] if d.get("id") == deposito_id_para_usar_int), None)

        if not deposito_alvo:
            print(f"{log_prefix}ERRO: Depósito Padrão com ID '{deposito_id_para_usar_int}' não foi encontrado na resposta da API para o ID alvo {target_id_for_stock}.")
            return None

        if sum_reserves_if_true:
            saldo_fisico = deposito_alvo.get("saldo")
            if isinstance(saldo_fisico, (int, float)):
                print(f"  -> {log_prefix}Retornando saldo FÍSICO do depósito '{deposito_alvo.get('nome')}': {saldo_fisico}")
                return float(saldo_fisico)
        else:
            saldo_disponivel = deposito_alvo.get("disponivel")
            if isinstance(saldo_disponivel, (int, float)):
                print(f"  -> {log_prefix}Retornando saldo DISPONÍVEL do depósito '{deposito_alvo.get('nome')}': {saldo_disponivel}")
                return float(saldo_disponivel)

        print(f"  -> {log_prefix}ERRO: Campo de saldo ('saldo' ou 'disponivel') não encontrado ou inválido no depósito '{deposito_alvo.get('nome')}'.")
        return None

    def _dispatch_ml_updates(self, item_id, actions, account_nickname, original_item_data) -> tuple[bool, list]:
        """
        [ORQUESTRADOR CORRIGIDO FINAL]
        - Envia SOMENTE os atributos selecionados para:
            * Itens sem variação (atributos no nível do item)
            * Itens com UMA única variação (atributos dentro da variação)
        - Mantém MERGE seguro para itens com múltiplas variações (evita perda de atributos)
        - Preserva demais comportamentos (preço, quantidade, título, descrição, envio, etc.)
        """
        # >>> FIX MIN: Desembrulhar quando vier {'actions_to_perform': {...}}
        if isinstance(actions, dict) and "actions_to_perform" in actions and isinstance(actions["actions_to_perform"], dict):
            actions = actions["actions_to_perform"]
        # Normalizar chaves
        actions = {str(k).strip(): v for k, v in (actions or {}).items()}
        # <<< END FIX MIN

        print(f"\n--- Orquestrador de Updates ML para Item: {item_id} (Conta: {account_nickname}) ---")
        try:
            print(f"  [Orq] Ações recebidas: {list(actions.keys())}", flush=True)
        except Exception:
            pass

        log_summary = []
        overall_success = True

        sku_for_price = self._get_sku_from_item_data(original_item_data)
        fixed_price_for_sku = self.fixed_prices.get(sku_for_price.upper()) if sku_for_price else None

        if fixed_price_for_sku is not None:
            print(f"    -> PREÇO FIXO ENCONTRADO para SKU '{sku_for_price}': R$ {fixed_price_for_sku:.2f}. Sobrescrevendo qualquer ação de preço.")
            actions["price"] = {"source": "manual", "value": float(fixed_price_for_sku)}
        elif "price" in actions and actions["price"].get("source") == "recalculate_new":
            print(f"    Recalculando preço para {item_id} para execução...")
            price_rules = actions["price"].get("value", {})
            cost_price_for_recalc = 0.0

            if sku_for_price:
                tiny_details = self.tiny_product_details_cache.get(sku_for_price)
                if not tiny_details:
                    tiny_id = self._get_tiny_product_id_by_sku(sku_for_price)
                    if tiny_id: tiny_details = self._get_tiny_product_details_v3(tiny_id)
                if tiny_details:
                    self.tiny_product_details_cache[sku_for_price] = tiny_details
                    precos_tiny = tiny_details.get("precos", {})
                    cost_price_for_recalc = float(precos_tiny.get("precoPromocional", 0.0) or 0.0) or float(precos_tiny.get("preco", 0.0) or 0.0)

            if cost_price_for_recalc > 0:
                calc_result = self._recalculate_price_unified(
                    account_data=self.ml_accounts.get(account_nickname), cost_price=cost_price_for_recalc, rules=price_rules,
                    category_id=original_item_data.get("category_id"),
                    listing_type_id=original_item_data.get("listing_type_id"), item_id=item_id
                )
                self.bulk_price_recalc_logs.append({
                    "account": account_nickname, "item_id": item_id,
                    "final_status_summary": "OK" if not calc_result.get("error") else f"ERRO: {calc_result.get('error')}",
                    "calculation_details": calc_result.get("calculation_details", [])
                })
                if not calc_result.get("error"):
                    actions["price"] = {"source": "manual", "value": calc_result.get("final_price")}
                else:
                    del actions["price"]
                    print(f"    ERRO ao recalcular preço para {item_id}. Ação de preço removida da tarefa.")
            else:
                del actions["price"]
                print(f"    Custo do produto não encontrado para {item_id}. Ação de preço removida.")

        token = self._get_current_ml_access_token_for_account(account_nickname)
        if not token:
            return False, [f"ERRO: Falha ao obter token para '{account_nickname}'."]

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
            'User-Agent': APP_USER_AGENT
        }

        main_put_payload = {}
        # <<<<<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA ALTERAÇÃO 1/2 >>>>>>>>>>>>>>>>>>>>>>>>>
        # A variável 'description_to_update' não é mais necessária aqui.
        # description_to_update = None 
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA ALTERAÇÃO 1/2 >>>>>>>>>>>>>>>>>>>>>>>>>
        compatibilities_to_update = None
        sku_to_update = None    

        variations_from_original = original_item_data.get("variations", [])
        has_variations = isinstance(variations_from_original, list) and bool(variations_from_original)
        variations_payload_map = {var['id']: {"id": var['id']} for var in variations_from_original if var.get('id')} if has_variations else {}


        if "add_main_image" in actions:
            new_main_image_url = actions["add_main_image"].get("value")
            if new_main_image_url:
                log_summary.append(f"  - Imagem Principal: Preparando para adicionar '{new_main_image_url[:40]}...'.")
                new_pictures_payload = [{"source": new_main_image_url}]
                existing_pictures = original_item_data.get("pictures", [])
                for pic in existing_pictures:
                    if pic.get("id"):
                        new_pictures_payload.append({"id": pic["id"]})
                if len(new_pictures_payload) > 12:
                    log_summary.append(f"    - AVISO: Total de imagens ({len(new_pictures_payload)}) excede o limite de 12. As últimas serão descartadas.")
                    new_pictures_payload = new_pictures_payload[:12]
                main_put_payload["pictures"] = new_pictures_payload
                actions.pop("pictures", None)

        if "price" in actions and actions["price"].get("value") is not None:
            new_price = actions["price"]["value"]
            if has_variations:
                for var_id in variations_payload_map:
                    variations_payload_map[var_id]['price'] = round(float(new_price), 2)
            else:
                main_put_payload["price"] = round(float(new_price), 2)

        if "available_quantity" in actions and actions["available_quantity"].get("source") == "from_tiny_qty":
            print(f"    Buscando estoque do Tiny para {item_id} antes da execução...")
            sku_for_stock = self._get_sku_from_item_data(original_item_data)
            if sku_for_stock:
                tiny_id_for_stock = None
                params_find_id = {'codigo': sku_for_stock.strip(), 'limit': 1}
                response_find_id = self._tiny_api_v3_request('GET', '/produtos', params=params_find_id)
                if response_find_id and response_find_id.get("itens"):
                    tiny_id_for_stock = str(response_find_id["itens"][0].get("id"))
                if tiny_id_for_stock:
                    sum_reserves_flag = self.update_qty_sync_tiny_var.get() if hasattr(self, 'update_qty_sync_tiny_var') else False
                    stock_from_tiny = self._get_tiny_available_stock_v3(tiny_id_for_stock, sum_reserves_if_true=sum_reserves_flag)
                    if stock_from_tiny is not None:
                        stock_to_send = int(stock_from_tiny)
                        if stock_to_send < 0:
                            print(f"    AVISO: Estoque do Tiny para SKU '{sku_for_stock}' (ID: {tiny_id_for_stock}) é negativo ({stock_to_send}). Ajustando para 0.")
                            stock_to_send = 0
                        actions["available_quantity"] = {"source": "manual", "value": stock_to_send}
                        print(f"    Estoque Tiny (ID: {tiny_id_for_stock}) encontrado e ajustado: {stock_to_send}. Ação de quantidade atualizada para 'manual'.")
                    else:
                        print(f"    ERRO ao buscar estoque do Tiny para SKU '{sku_for_stock}' (ID: {tiny_id_for_stock}). Ação de quantidade removida.")
                        del actions["available_quantity"]
                else:
                    print(f"    ERRO: SKU '{sku_for_stock}' não encontrado no Tiny. Ação de quantidade removida.")
                    del actions["available_quantity"]
            else:
                print(f"    ERRO: SKU não encontrado no anúncio {item_id}. Ação de quantidade removida.")
                del actions["available_quantity"]
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO PONTUAL >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        # Lógica para adicionar 'available_quantity' ao payload, APÓS ter sido resolvida do Tiny
        if "available_quantity" in actions and actions["available_quantity"].get("value") is not None:
            new_qty = actions["available_quantity"]["value"]
            if has_variations:
                # Se o anúncio tem variações, a quantidade é definida em cada variação
                for var_id in variations_payload_map:
                    variations_payload_map[var_id]['available_quantity'] = int(new_qty)
                print(f"    -> Quantidade {new_qty} preparada para TODAS as {len(variations_payload_map)} variações.", flush=True)
            else:
                # Se é um anúncio simples, a quantidade vai no nível principal do payload
                main_put_payload["available_quantity"] = int(new_qty)
                print(f"    -> Quantidade {new_qty} preparada para o item simples.", flush=True)
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO PONTUAL >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        if "pictures" in actions and actions["pictures"].get("value"):
            new_pictures_payload = actions["pictures"]["value"]
            main_put_payload["pictures"] = new_pictures_payload
            if has_variations:
                new_picture_sources = [p['source'] for p in new_pictures_payload if p.get('source')]
                for var_id in variations_payload_map:
                    variations_payload_map[var_id]['picture_ids'] = new_picture_sources

        if has_variations and any(('price' in v or 'available_quantity' in v or 'picture_ids' in v) for v in variations_payload_map.values()):
            final_variations_payload = [v for v in variations_payload_map.values() if len(v) > 1]
            if final_variations_payload:
                main_put_payload["variations"] = final_variations_payload

        for field in ["title", "status"]:
            if field in actions and actions[field].get("value") is not None:
                main_put_payload[field] = actions[field]["value"]

        if "mfg_time" in actions:
            VALID_SALE_TERMS_TO_PRESERVE = {"WARRANTY_TYPE", "WARRANTY_TIME", "INVOICE"}
            final_sale_terms = [st for st in original_item_data.get("sale_terms", []) if isinstance(st, dict) and st.get("id") in VALID_SALE_TERMS_TO_PRESERVE]
            value = actions["mfg_time"].get("value")
            try:
                num_dias = int(str(value).strip())
                if num_dias > 0:
                    final_sale_terms.append({"id": "MANUFACTURING_TIME", "value_name": f"{num_dias} dias"})
            except (ValueError, TypeError): pass
            main_put_payload["sale_terms"] = final_sale_terms

        if "attributes_json" in actions:
            attributes_to_update = actions["attributes_json"].get("value")
            def _sanitize_ml_attribute(attr: dict) -> dict:
                allowed = {"id", "name", "value_id", "value_name", "value_struct", "values"}
                return {k: v for k, v in (attr or {}).items() if k in allowed and v is not None}
            if isinstance(attributes_to_update, list) and attributes_to_update:
                attributes_to_update = [_sanitize_ml_attribute(a) for a in attributes_to_update if isinstance(a, dict) and a.get("id")]
                if attributes_to_update:
                    if has_variations and len(variations_payload_map) == 1:
                        only_var_id = next(iter(variations_payload_map))
                        variations_payload_map[only_var_id]["attributes"] = attributes_to_update
                        existing_vars = {v["id"]: v for v in main_put_payload.get("variations", []) if isinstance(v, dict) and v.get("id")}
                        if only_var_id in existing_vars:
                            existing_vars[only_var_id].update(variations_payload_map[only_var_id])
                            main_put_payload["variations"] = list(existing_vars.values())
                        else:
                            main_put_payload["variations"] = [variations_payload_map[only_var_id]]
                    elif not has_variations:
                        main_put_payload["attributes"] = attributes_to_update
                    else:
                        original_attributes = original_item_data.get("attributes", [])
                        original_attrs_map = {a['id']: a for a in original_attributes if a.get('id')}
                        if 'ITEM_CONDITION' not in original_attrs_map:
                            original_attrs_map['ITEM_CONDITION'] = {'id': 'ITEM_CONDITION', 'value_id': '2230284'}
                        for attr_change in attributes_to_update:
                            original_attrs_map[attr_change["id"]] = attr_change
                        main_put_payload["attributes"] = list(original_attrs_map.values())

        if "description" in actions: description_to_update = actions["description"].get("value")
        # <<<<<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA ALTERAÇÃO 2/2 >>>>>>>>>>>>>>>>>>>>>>>>>
        # A lógica da descrição é movida para DENTRO da montagem do payload principal.
        if "description" in actions:
            description_text = actions["description"].get("value")
            if description_text is not None:
                # Converte para texto simples e adiciona ao payload principal
                plain_text_for_api = strip_html_tags(description_text)
                if plain_text_for_api:
                    main_put_payload["description"] = {"plain_text": plain_text_for_api}
                    log_summary.append("  - Descrição: Preparada para envio no payload principal.")
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA ALTERAÇÃO 2/2 >>>>>>>>>>>>>>>>>>>>>>>>>    
        if "seller_sku_ml" in actions: sku_to_update = actions["seller_sku_ml"].get("value")
        if "compatibilities" in actions:
            profile_name = actions["compatibilities"].get("value")
            if isinstance(profile_name, str) and profile_name:
                profile_data = self.db_manager.load_compatibility_profile_from_db(profile_name)
                if profile_data and "compatibilities_list" in profile_data:
                    compatibilities_to_update = profile_data["compatibilities_list"]
                else:
                    log_summary.append(f"  - Compat.: ERRO - Perfil '{profile_name}' não encontrado no DB.")
                    overall_success = False

        shipping_modified = False
        shipping_payload = original_item_data.get("shipping", {}).copy()
        acc_shipping_mode = self.ml_accounts.get(account_nickname, {}).get("shipping_mode", "me2").lower()
        if "package_dimensions_group" in actions:
            shipping_modified = True
            h = actions.get("seller_package_height", {}).get("value")
            w = actions.get("seller_package_width", {}).get("value")
            l = actions.get("seller_package_length", {}).get("value")
            wt = actions.get("seller_package_weight", {}).get("value")
            if all(v is not None for v in [h, w, l, wt]):
                if acc_shipping_mode == "me2":
                    shipping_payload['dimensions'] = f"{int(h)}x{int(w)}x{int(l)},{int(float(wt)*1000)}"
                    log_summary.append("  - Dimensões: Atualizando campo 'shipping.dimensions' para ME2.")
                else:
                    if "attributes" not in main_put_payload: main_put_payload["attributes"] = []
                    ids_dimensoes = {"SELLER_PACKAGE_HEIGHT", "SELLER_PACKAGE_WIDTH", "SELLER_PACKAGE_LENGTH", "SELLER_PACKAGE_WEIGHT", "SELLER_PACKAGE_TYPE"}
                    main_put_payload["attributes"] = [a for a in main_put_payload.get("attributes", []) if a.get("id") not in ids_dimensoes]
                    main_put_payload["attributes"].extend([
                        {"id": "SELLER_PACKAGE_HEIGHT", "value_name": f"{int(h)} cm"},
                        {"id": "SELLER_PACKAGE_WIDTH", "value_name": f"{int(w)} cm"},
                        {"id": "SELLER_PACKAGE_LENGTH", "value_name": f"{int(l)} cm"},
                        {"id": "SELLER_PACKAGE_WEIGHT", "value_name": f"{int(float(wt)*1000)} g"},
                        {"id": "SELLER_PACKAGE_TYPE", "value_id": "47115155"}
                    ])
                    log_summary.append("  - Dimensões: Atualizando como atributos para ME1/Outro.")
        if "local_pickup_update" in actions:
            shipping_modified = True
            value = actions["local_pickup_update"].get("value")
            if value == "Sim": shipping_payload['local_pick_up'] = True
            elif value == "Não": shipping_payload['local_pick_up'] = False
        if shipping_modified:
            main_put_payload['shipping'] = shipping_payload
        # <<<<<<<<<<<<<<<<<<<< ADICIONE ESTA LINHA EXATAMENTE AQUI >>>>>>>>>>>>>>>>>>>>
        print(f"  [Orq] Payload final preparado para o PUT principal: {json.dumps(main_put_payload)}", flush=True)
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA ADIÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        if main_put_payload:
            success, msg = self._update_item_main_payload(item_id, main_put_payload, headers)
            log_summary.append(f"  - Ação Principal (Título/Preço/Ficha Téc./etc.): {msg}")
            if not success: overall_success = False
            else: self._add_to_modified_history(item_id, account_nickname)

        # <<<<<<<<<<<<<<<<<<<<<<<<<<< REMOÇÃO DO BLOCO ANTIGO >>>>>>>>>>>>>>>>>>>>>>>>>
        # O bloco de código abaixo, que estava no final, foi removido, pois a lógica
        # agora está dentro do 'main_put_payload'.
        #
        # if description_to_update is not None and overall_success:
        #     success, msg = self._update_item_description(item_id, description_to_update, headers)
        #     log_summary.append(f"  - Descrição: {msg}")
        #     if not success: overall_success = False
        #     else: self._add_to_modified_history(item_id, account_nickname)
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA REMOÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>

        if sku_to_update is not None and overall_success:
            success, msg = self._update_item_sku(item_id, sku_to_update, headers)
            log_summary.append(f"  - SKU: {msg}")
            if not success: overall_success = False
            else: self._add_to_modified_history(item_id, account_nickname)

        if compatibilities_to_update is not None and overall_success:
            success, msg = self._update_item_compatibilities(item_id, compatibilities_to_update, headers)
            log_summary.append(f"  - Compatibilidades: {msg}")
            if not success: overall_success = False
            else: self._add_to_modified_history(item_id, account_nickname)
            
        # BLOCO DE POSIÇÃO (agora vai encontrar a chave)
        alias_pos_key = "position_compatibility" if "position_compatibility" in actions else ("position" if "position" in actions else None)
        if alias_pos_key and overall_success:
            position_raw = actions.get(alias_pos_key, {}).get("value")
            position_value = (str(position_raw).strip() if position_raw is not None else None)
            if position_value:
                print(f"  [Orq] Atualizando Posição de Compatibilidade -> '{position_value}'", flush=True)
                success, msg = self._update_item_compatibility_positions(item_id, position_value, headers)
                print(f"  [Orq] Posição: {msg}", flush=True)
                log_summary.append(f"  - Posição: {msg}")
                if not success: overall_success = False
                else: self._add_to_modified_history(item_id, account_nickname)

        print("--- Fim do Orquestrador de Updates ---")
        return overall_success, log_summary


    def _update_bulk_status_for_item(self, item_id_ml, status_message, new_price=None):
        """
        Atualiza o status e opcionalmente o preço de um item na Treeview de Edição em Massa.
        """
        if not hasattr(self, 'bulk_edit_ads_tree') or not self.bulk_edit_ads_tree.winfo_exists(): return

        tree_iid = next((iid for iid, mlb_id in self.bulk_edit_tree_item_map.items() if mlb_id == item_id_ml), None)
        if not tree_iid or not self.bulk_edit_ads_tree.exists(tree_iid): return

        try:
            current_values_list = list(self.bulk_edit_ads_tree.item(tree_iid, "values"))
            
            # Atualiza a coluna de status (índice 5: "status_display")
            if len(current_values_list) > 5:
                current_values_list[5] = status_message[:25]
            
            # <<<< NOVA LÓGICA: Atualiza o preço se um novo valor for fornecido >>>>
            if new_price is not None:
                # A coluna de preço é a de índice 6
                if len(current_values_list) > 6:
                    current_values_list[6] = f"{new_price:.2f}"
            # <<<< FIM DA NOVA LÓGICA >>>>

            self.bulk_edit_ads_tree.item(tree_iid, values=tuple(current_values_list))
            
            tag_name = None
            if "ERRO" in status_message.upper() or "FALHA" in status_message.upper():
                tag_name = f"error_row_{tree_iid}"
                self.bulk_edit_ads_tree.tag_configure(tag_name, background="pink")
            elif "OK" in status_message.upper() or "SUCESSO" in status_message.upper():
                tag_name = f"success_row_{tree_iid}"
                self.bulk_edit_ads_tree.tag_configure(tag_name, background="#d9ead3")
            
            if tag_name:
                # Remove tags de status anteriores antes de adicionar a nova
                current_tags = list(self.bulk_edit_ads_tree.item(tree_iid, "tags"))
                tags_to_remove = [t for t in current_tags if t.startswith("error_row_") or t.startswith("success_row_")]
                for t in tags_to_remove:
                    current_tags.remove(t)
                current_tags.append(tag_name)
                self.bulk_edit_ads_tree.item(tree_iid, tags=tuple(current_tags))

        except Exception as e:
            print(f"Erro ao atualizar status na tree Aba 8 para {item_id_ml}: {e}")

    def _finalize_bulk_edit_processing(self):
        """
        [CORRIGIDO] Chamado quando a fila de edição em massa está vazia para mostrar resumos.
        """
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.config(cursor="") 
            
            # Atualiza a treeview para refletir os status finais
            if hasattr(self, '_apply_bulk_edit_ads_filters_and_sort'):
                self._apply_bulk_edit_ads_filters_and_sort(error_messages_initial_fetch=None) 
            
            final_status_msg = "Processamento em lote concluído. Verifique os status na lista."
            
            # Verifica se há logs de recálculo de preço para exibir
            if self.bulk_price_recalc_logs:
                print(f"Finalizando... {len(self.bulk_price_recalc_logs)} logs de cálculo de preço para exibir no relatório.")
                self._show_bulk_price_recalc_summary() 
                final_status_msg += " Detalhes do cálculo de preço em nova janela."
                # Limpa o log DEPOIS de exibir o relatório, para a próxima execução.
                self.bulk_price_recalc_logs.clear() 
            else:
                print("Finalizando... Nenhum log de recálculo de preço gerado nesta execução.")

            if hasattr(self, 'bulk_edit_ads_status_label'):
                self.bulk_edit_ads_status_label.config(text=final_status_msg)
            
            print("Finalize Bulk Edit Processing: UI atualizada.")


    def _open_abc_import_dialog(self):
        # 1) Abre o diálogo para escolher "Valor" ou "Quantidade"
        dlg = ABCCurveImportDialog(self.root)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return  # usuário cancelou

        # 2) Seleciona o arquivo .xlsx
        from tkinter import filedialog
        filepath = filedialog.askopenfilename(
            parent=self.root,
            title="Selecione a planilha da Curva ABC",
            filetypes=[("Excel", "*.xlsx")]
        )
        if not filepath:
            return  # usuário cancelou

        # 3) Importa a planilha (gera DataFrame padronizado com SKU/Valor/Quantidade/Classe_ABC)
        importer = ABCImporter(sort_by=dlg.result)  # "Valor" ou "Quantidade"
        result = importer.import_file(filepath)
        if not result.success:
            messagebox.showerror("Erro", result.message, parent=self.root)
            return

        if result.warnings:
            print("[ABCImporter] Avisos:", "; ".join(result.warnings))

        # 4) Aplica no banco (tiny_products): vendas_qtd/valor, curva_a_posicao, curva_a_rank, import_sequence
        svc = ABCService()
        report = svc.apply_to_db(self.db_manager, result.df)

        if report.warnings:
            print("[ABCService] Avisos:", "; ".join(report.warnings))
        if report.not_found:
            # Mostra só os primeiros para não poluir
            preview = ", ".join(report.not_found[:30])
            print(f"[ABCService] SKUs não encontrados ({len(report.not_found)}): {preview}{' ...' if len(report.not_found) > 30 else ''}")

        # 5) Feedback ao usuário
        messagebox.showinfo(
            "Curva ABC",
            f"{report.message}\n\nAtualizados: {report.updated}\nNão encontrados: {len(report.not_found or [])}",
            parent=self.root
        )



    # -------------------------------------------------
    # Ações de Menu
    # -------------------------------------------------
    def _open_queue_manager(self):
        UnifiedQueueManagerWindow(self.root, self)


    # -------------------------------------------------
    # Loop Principal
    # -------------------------------------------------
    def run(self):
        self.root.mainloop()
