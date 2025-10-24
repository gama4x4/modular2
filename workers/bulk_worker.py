import json
import threading
import traceback
import time
from tkinter import messagebox


class BulkWorker(threading.Thread):
    """
    Gerencia as ações da Aba 8 (Edição em Massa).
    Encapsula execução em thread e acesso ao DB e à API ML.
    """

    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        # aliases para o DB (compatibilidade)
        self.db = app.db_manager
        self.db_manager = app.db_manager
        self._stop_event = threading.Event()
        self._is_running = False

    # ============================
    # MÉTODOS DO SEU CÓDIGO REAL
    # ============================

    def _execute_bulk_item_actions(self, account_nickname, item_id, task_data, original_item_data_from_ui):
        """
        [CORRIGIDO V-FINAL] Executa ações, FORÇANDO o uso de preço fixo e buscando o estoque
        da variação correta (não do pai).
        """
        print(f"  [EXECUTE_BULK] Iniciando ações para {item_id} na conta {account_nickname}")
        
        actions = task_data.get("actions_to_perform", {}).copy()

        if not actions:
            return True, "Nenhuma ação configurada."

        # 1) Preço fixo por SKU (se houver)
        sku_for_price = self._get_sku_from_item_data(original_item_data_from_ui)
        fixed_price_for_sku = self.app.fixed_prices.get(sku_for_price.upper()) if sku_for_price else None

        if fixed_price_for_sku is not None:
            print(f"    -> PREÇO FIXO ENCONTRADO para SKU '{sku_for_price}': R$ {fixed_price_for_sku:.2f}. Sobrescrevendo qualquer ação de preço.")
            actions["price"] = {"source": "manual", "value": float(fixed_price_for_sku)}

        # 2) Quantidade: busca no Tiny **da variação correta** (via consulta pelo código/SKU)
        if "available_quantity" in actions and actions["available_quantity"].get("source") == "from_tiny_qty":
            print(f"    Buscando estoque do Tiny para {item_id} antes da execução...")
            sku_for_stock = self._get_sku_from_item_data(original_item_data_from_ui)

            if sku_for_stock:
                # <<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO PRINCIPAL >>>>>>>>>>>>>>>>>>>>
                tiny_id_for_stock = None
                params_find_id = {'codigo': sku_for_stock.strip(), 'limit': 1}
                response_find_id = self.app._tiny_api_v3_request('GET', '/produtos', params=params_find_id)
                if response_find_id and response_find_id.get("itens"):
                    tiny_id_for_stock = str(response_find_id["itens"][0].get("id"))
                # <<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO PRINCIPAL >>>>>>>>>>>>>>>>>>>>>>

                if tiny_id_for_stock:
                    # pode ser tk.BooleanVar ou bool; tratamos os dois casos
                    sum_reserves_flag = False
                    if hasattr(self.app, 'update_qty_sync_tiny_var'):
                        var = self.app.update_qty_sync_tiny_var
                        sum_reserves_flag = var.get() if hasattr(var, 'get') else bool(var)

                    stock_from_tiny = self.app._get_tiny_available_stock_v3(
                        tiny_id_for_stock,
                        sum_reserves_if_true=sum_reserves_flag
                    )

                    if stock_from_tiny is not None:
                        stock_to_send = int(stock_from_tiny)
                        if stock_to_send < 0:
                            print(f"    AVISO: Estoque do Tiny para SKU '{sku_for_stock}' (ID: {tiny_id_for_stock}) é negativo ({stock_to_send}). Ajustando para 0.")
                            stock_to_send = 0
                        
                        # IMPORTANTÍSSIMO: coloca a qty como 'manual' já resolvida aqui
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

        # 3) Despacha para o orquestrador que MONTA o payload final e envia ao ML
        success, summary_list = self.app._dispatch_ml_updates(
            item_id,
            {"actions_to_perform": actions},
            account_nickname,
            original_item_data_from_ui
        )
        summary_text = "\n".join(summary_list)
        return success, summary_text

    def _process_bulk_edit_queue_worker(self):
        """[CORRIGIDO] Worker que processa a fila de edição em massa, agora respondendo a um evento."""
        if self.app.is_bulk_processing_active:
            return
        self.app.is_bulk_processing_active = True
        print("[BULK WORKER] Iniciado.")
        while True:
            # Espera por um sinal (timeout de 10s para verificação periódica)
            self.app.bulk_edit_worker_event.wait(timeout=10)
            self.app.bulk_edit_worker_event.clear()

            processed_in_this_batch = False
            while True:  # Loop interno para processar todas as tarefas pendentes
                tasks = self.db_manager.get_tasks_from_queue(task_type='BULK_EDIT', status='PENDING', limit=10)
                if not tasks:
                    break  # Fila vazia, sai do loop interno
                
                processed_in_this_batch = True
                for task in tasks:
                    task_id, item_id, nickname = task['task_id'], task['item_id'], task['account_nickname']
                    self.db_manager.update_task_status(task_id, 'PROCESSING')
                    try:
                        payload = json.loads(task['payload_json'])
                        actions = payload['actions_to_perform']
                        original_data = payload['original_item_data']
                        
                        success, error_message = self._execute_bulk_item_actions(
                            nickname, item_id, {"actions_to_perform": actions}, original_data
                        )
                        
                        if success:
                            self.db_manager.delete_tasks_from_queue([task_id])
                            self.app.root.after(0, self.app._update_bulk_status_for_item, item_id, "OK", None)
                        else:
                            raise Exception(error_message)
                    except Exception as e:
                        self.db_manager.update_task_status(task_id, 'ERROR', str(e))
                        self.app.root.after(0, self.app._update_bulk_status_for_item, item_id, f"ERRO: {str(e)[:30]}", None)
                    time.sleep(0.5)
            
            if processed_in_this_batch:
                self.app.root.after(0, self.app._finalize_bulk_edit_processing)

    def _get_sku_from_item_data(self, item_data_dict):
        """
        Extrai o SKU de um dicionário de dados do item, com logging detalhado.
        Prioriza os dados da variação sobre os do item principal.
        Prioridade: 
        1. Variação (Atributo SELLER_SKU)
        2. Variação (Campo seller_custom_field)
        3. Variação (Atributo PART_NUMBER)
        4. Item (Atributo SELLER_SKU)
        5. Item (Campo seller_custom_field)
        6. Item (Atributo PART_NUMBER)
        """
        if not item_data_dict or not isinstance(item_data_dict, dict):
            return None
        
        # PRIORIDADE MÁXIMA: SKU injetado durante a busca (garante variação correta)
        injected_sku = item_data_dict.get('_correct_sku_from_search')
        if injected_sku and injected_sku.strip():
            return injected_sku.strip()

        # --- 1, 2, 3. Tenta encontrar SKU DENTRO das variações primeiro ---
        variations = item_data_dict.get("variations", [])
        if isinstance(variations, list) and variations:
            for variation in variations:
                if not isinstance(variation, dict):
                    continue

                # 1. Atributo 'SELLER_SKU' da variação
                var_attributes = variation.get("attributes", [])
                if isinstance(var_attributes, list):
                    for var_attr in var_attributes:
                        if isinstance(var_attr, dict) and var_attr.get("id") == "SELLER_SKU":
                            found_sku = var_attr.get("value_name")
                            if found_sku and found_sku.strip():
                                return found_sku.strip()
                
                # 2. Campo 'seller_custom_field' da variação
                found_sku = variation.get("seller_custom_field")
                if found_sku and found_sku.strip():
                    return found_sku.strip()

                # 3. Atributo 'PART_NUMBER' da variação
                if isinstance(var_attributes, list):
                    for var_attr in var_attributes:
                        if isinstance(var_attr, dict) and var_attr.get("id") == "PART_NUMBER":
                            found_sku = var_attr.get("value_name")
                            if found_sku and found_sku.strip():
                                return found_sku.strip()
        
        attributes = item_data_dict.get("attributes", [])
        # 4. Atributo 'SELLER_SKU' no item
        if isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict) and attr.get("id") == "SELLER_SKU":
                    found_sku = attr.get("value_name")
                    if found_sku and found_sku.strip():
                        return found_sku.strip()

        # 5. Campo 'seller_custom_field' do item
        found_sku = item_data_dict.get("seller_custom_field")
        if found_sku and found_sku.strip():
            return found_sku.strip()

        # 6. Atributo 'PART_NUMBER' no item
        if isinstance(attributes, list):
            for attr in attributes:
                if isinstance(attr, dict) and attr.get("id") == "PART_NUMBER":
                    found_sku = attr.get("value_name")
                    if found_sku and found_sku.strip():
                        return found_sku.strip()

        return None

    # -------------------------------------------------
    # LOOP THREAD — chama o worker real
    # -------------------------------------------------
    def run(self):
        self._is_running = True
        print("[BulkWorker] Thread iniciada.")
        try:
            self._process_bulk_edit_queue_worker()
        except Exception as e:
            print("[BulkWorker] ERRO:", e)
            traceback.print_exc()
            try:
                messagebox.showerror("Erro no BulkWorker", str(e), parent=self.app.root)
            except Exception:
                pass
        finally:
            self._is_running = False
            print("[BulkWorker] Finalizado.")
