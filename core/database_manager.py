import sqlite3
import threading
import os
import sys
import pandas as pd
from tkinter import messagebox

class DatabaseManager:
    """
    Classe central responsável por manipular o banco de dados SQLite.
    Este é apenas o esqueleto — cole aqui os métodos reais do seu código
    (como _execute_query, get_tasks_from_queue, add_task_to_queue, etc.)
    """

    def __init__(self, db_path=None):
        """
        Inicializa o banco de dados.
        Caso você queira manter o mesmo comportamento do seu sistema atual,
        copie o conteúdo completo do seu método original __init__ aqui.
        """
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            # no sistema modular, subimos uma pasta para salvar o DB fora de /core/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        db_filename = 'app_data.db'
        final_db_path = os.path.join(base_dir, db_filename)
        self.db_name = db_path or final_db_path

        # --- FIM DA LÓGICA ROBUSTA ---

        self.thread_local = threading.local()
        try:
            os.makedirs(os.path.dirname(self.db_name), exist_ok=True)
            conn = sqlite3.connect(self.db_name)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode=WAL;")
            cursor = conn.cursor()
            self._create_tables_with_cursor(cursor)
            conn.commit()
            conn.close()
            print(f"DatabaseManager initialized. DB Path: {self.db_name}")
        except sqlite3.Error as e:
            critical_msg = f"CRITICAL DATABASE ERROR on initialization: {e}\nDatabase path: {self.db_name}\nApplication cannot continue."
            print(critical_msg)
            messagebox.showerror("Fatal Database Error", critical_msg)
            sys.exit(f"Fatal DB Error: {e}")


    def _ensure_db_ready(self):
        """Cria o banco se não existir (placeholder simples)."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.close()
        except Exception as e:
            messagebox.showerror("Erro ao inicializar DB", str(e))
            sys.exit(1)

    def update_task_result(self, task_id, result_message):
        """[UNIFICADO] Define o status de uma tarefa como DONE e salva sua mensagem de resultado."""
        query = "UPDATE unified_task_queue SET status = 'DONE', last_error_message = ? WHERE task_id = ?"
        self._execute_query(query, (result_message, task_id), commit=True)

    def add_task_to_queue(self, task_type: str, account_nickname: str, item_id: str = None, payload: dict = None, delay_minutes: int = 0):
        """[CORRIGIDO] Adiciona QUALQUER tarefa à fila unificada."""
        payload_json = json.dumps(payload, ensure_ascii=False) if payload else '{}'
        scheduled_time = datetime.now() + timedelta(minutes=delay_minutes)
        query = """
            INSERT INTO unified_task_queue (task_type, account_nickname, item_id, payload_json, scheduled_for)
            VALUES (?, ?, ?, ?, ?)
        """
        try:
            self._execute_query(query, (task_type, account_nickname, item_id, payload_json, scheduled_time), commit=True)
            print(f"DB: Tarefa '{task_type}' para item '{item_id or 'N/A'}' adicionada à fila unificada.")
            return True
        except Exception as e:
            print(f"DB: Erro ao adicionar tarefa '{task_type}' à fila: {e}")
            return False

    def get_tasks_from_queue(self, task_type: str = None, status: str = 'PENDING', limit: int = 10, task_ids: list = None):
        """[CORRIGIDO] Busca tarefas da fila unificada. Pode filtrar por tipo, status ou IDs."""
        base_query = "SELECT * FROM unified_task_queue"
        conditions = []
        params = []

        if task_ids:
            placeholders = ','.join('?' for _ in task_ids)
            conditions.append(f"task_id IN ({placeholders})")
            params.extend(task_ids)
        else:
            if task_type:
                conditions.append("task_type = ?")
                params.append(task_type)
            if status:
                conditions.append("status = ?")
                params.append(status)
        
        if conditions:
            base_query += " WHERE " + " AND ".join(conditions)
        
        base_query += " ORDER BY added_timestamp ASC"
        if limit is not None:
            base_query += " LIMIT ?"
            params.append(limit)

        rows = self._execute_query(base_query, tuple(params), fetch_all=True)
        return [dict(row) for row in rows] if rows else []
    
    def update_task_status(self, task_id, new_status, error_message=None, increment_retry=True):
        """[UNIFICADO] Atualiza o status, mensagem e opcionalmente o contador de retentativas de uma tarefa."""
        set_clauses = ["status = ?", "last_error_message = ?"]
        params = [new_status, error_message]
        
        if increment_retry:
            set_clauses.append("retry_count = retry_count + 1")
        
        query = f"UPDATE unified_task_queue SET {', '.join(set_clauses)} WHERE task_id = ?"
        params.append(task_id)
        
        self._execute_query(query, tuple(params), commit=True)

    def delete_tasks_from_queue(self, task_ids: list):
        """[UNIFICADO] Remove tarefas da fila unificada por seus IDs."""
        if not task_ids: return
        query = f"DELETE FROM unified_task_queue WHERE task_id IN ({','.join('?' for _ in task_ids)})"
        self._execute_query(query, tuple(task_ids), commit=True)

    def reset_tasks_by_ids(self, task_ids: list):
        """[UNIFICADO] Reseta o status e o contador de retentativas para tarefas com erro."""
        if not task_ids: return 0
        now_local = datetime.now()
        placeholders = ','.join('?' for _ in task_ids)
        query = f"""
            UPDATE unified_task_queue
            SET status = 'PENDING', retry_count = 0, last_error_message = NULL, scheduled_for = ?
            WHERE task_id IN ({placeholders})
        """
        params = (now_local,) + tuple(task_ids)
        cursor = self._execute_query(query, params, commit=True)
        return cursor.rowcount if cursor else 0

    def clear_all_tasks_from_queue(self):
        """[UNIFICADO] Limpa todas as tarefas da fila unificada."""
        self._execute_query("DELETE FROM unified_task_queue", commit=True)
            
    def update_product_abc_sales_data(self, sku, qtd, valor):
        """Atualiza os dados de vendas (Qtd e Valor) para um SKU específico."""
        query = "UPDATE tiny_products SET vendas_qtd = ?, vendas_valor = ? WHERE sku = ?"
        self._execute_query(query, (qtd, valor, sku), commit=True)


    def clear_all_abc_positions(self):
        """Reseta a classificação ABC, vendas e sequência para todos os produtos."""
        query = "UPDATE tiny_products SET curva_a_posicao = NULL, curva_a_rank = NULL, import_sequence = NULL, vendas_qtd = 0, vendas_valor = 0"
        self._execute_query(query, commit=True)
        print("DB: Classificação ABC, dados de vendas e sequência de importação foram limpos para todos os produtos.")

    def save_product_group(self, group_name, description, sku_list):
        """Salva ou atualiza um grupo de produtos e seus SKUs."""
        conn = self._get_thread_connection()
        try:
            with conn:
                # Insere ou ignora o grupo para obter o ID
                cursor = conn.cursor()
                cursor.execute("INSERT OR IGNORE INTO product_groups (group_name, description) VALUES (?, ?)", (group_name, description))
                
                # Obtém o ID do grupo (existente ou recém-criado)
                cursor.execute("SELECT group_id FROM product_groups WHERE group_name = ?", (group_name,))
                group_id_row = cursor.fetchone()
                if not group_id_row:
                    return False, "Falha ao obter ID do grupo."
                group_id = group_id_row['group_id']

                # Atualiza a descrição, caso o grupo já existisse
                cursor.execute("UPDATE product_groups SET description = ? WHERE group_id = ?", (description, group_id))

                # Gerencia os SKUs associados (apaga os antigos e insere os novos)
                cursor.execute("DELETE FROM product_group_skus WHERE group_id = ?", (group_id,))
                if sku_list:
                    skus_to_insert = [(group_id, sku.strip().upper()) for sku in sku_list]
                    cursor.executemany("INSERT INTO product_group_skus (group_id, sku) VALUES (?, ?)", skus_to_insert)
            
            return True, "Grupo salvo com sucesso."
        except sqlite3.Error as e:
            return False, f"Erro no DB: {e}"

    def get_all_product_groups_with_skus(self):
        """Busca todos os grupos e os SKUs associados a cada um."""
        query = """
            SELECT 
                pg.group_id, 
                pg.group_name, 
                pg.description, 
                GROUP_CONCAT(pgs.sku, ', ') as skus
            FROM product_groups pg
            LEFT JOIN product_group_skus pgs ON pg.group_id = pgs.group_id
            GROUP BY pg.group_id, pg.group_name, pg.description
            ORDER BY pg.group_name;
        """
        rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def delete_product_group(self, group_id):
        """Deleta um grupo de produtos (ON DELETE CASCADE cuidará das tabelas filhas)."""
        self._execute_query("DELETE FROM product_groups WHERE group_id = ?", (group_id,), commit=True)

    def add_competitor_ad(self, mlb_id, url, linked_group_id, parent_sku, title, price, stock):
        """[CORRIGIDO] Adiciona ou atualiza um anúncio de concorrente monitorado, incluindo o parent_sku."""
        query = """
            INSERT OR REPLACE INTO competitor_ads 
            (mlb_id, url, linked_group_id, parent_sku, last_known_title, last_known_price, last_known_stock, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """
        # A correção principal é adicionar 'parent_sku' aos parâmetros.
        params = (mlb_id, url, linked_group_id, parent_sku, title, price, stock)
        self._execute_query(query, params, commit=True)
        return self._execute_query("SELECT changes()", fetch_one=True)[0]

    def get_competitors_for_group(self, group_id):
        """Busca todos os concorrentes de um grupo específico."""
        rows = self._execute_query("SELECT * FROM competitor_ads WHERE linked_group_id = ?", (group_id,), fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def delete_competitor_ad(self, mlb_id):
        """Deleta um anúncio de concorrente da lista de monitoramento."""
        self._execute_query("DELETE FROM competitor_ads WHERE mlb_id = ?", (mlb_id,), commit=True)

    # DENTRO DA CLASSE DatabaseManager
    # SUBSTITUA ESTE MÉTODO INTEIRO
    def replace_all_tiny_products(self, df: pd.DataFrame) -> int:
        """
        [MODO HÍBRIDO E CORRIGIDO] Apaga todos os produtos Tiny e insere os novos a partir de um DataFrame,
        estabelecendo a relação pai-filho e NORMALIZANDO o campo de 'Situação' para 'A' ou 'I'.
        """
        self._execute_query("DELETE FROM tiny_products", commit=True)
        
        if 'Código (SKU)' in df.columns:
            df = df.drop_duplicates(subset=['Código (SKU)'], keep='first')

        sku_to_id_map = {}
        if 'Código (SKU)' in df.columns and 'ID' in df.columns:
            df['Código (SKU)'] = df['Código (SKU)'].astype(str)
            df['ID'] = pd.to_numeric(df['ID'], errors='coerce')
            sku_to_id_map = pd.Series(df.ID.values, index=df['Código (SKU)']).to_dict()

        rows_to_insert = []
        for idx, row in df.iterrows():
            parent_sku = None
            if 'Código do pai' in row and pd.notna(row['Código do pai']):
                parent_sku = str(row['Código do pai']).strip()
            parent_id = sku_to_id_map.get(parent_sku) if parent_sku else None

            # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            # Normaliza o campo 'Situação' para o formato 'A' (Ativo) ou 'I' (Inativo)
            situacao_from_sheet = str(row.get('Situação', 'Ativo')).strip().lower()
            status_for_db = 'A' if situacao_from_sheet == 'ativo' else 'I'
            # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
            
            rows_to_insert.append((
                row.get('ID', None),
                str(row['Código (SKU)']).strip() if 'Código (SKU)' in row else None,
                row.get('Descrição', ''),
                float(row.get('Peso bruto (Kg)', 0) or 0),
                float(row.get('Largura embalagem', 0) or 0),
                float(row.get('Altura embalagem', 0) or 0),
                float(row.get('Comprimento embalagem', 0) or 0),
                float(row.get('Estoque', 0) or 0),
                status_for_db, # <<<<<<<<<< USA A VARIÁVEL CORRIGIDA AQUI
                str(row.get('Classificação', '')) if pd.notna(row.get('Classificação')) else '',
                int(row.get('Rank', 9999)) if pd.notna(row.get('Rank')) else 9999,
                str(row.get('URL imagem 1', '')) if pd.notna(row.get('URL imagem 1')) else '',
                idx,
                parent_id
            ))

        valid_rows = [r for r in rows_to_insert if r[1]]
        
        insert_query = """
            INSERT OR REPLACE INTO tiny_products (
                id_produto, sku, descricao, peso, largura, altura,
                profundidade, stock, status, curva_a_posicao, curva_a_rank, 
                url_imagem_1, import_sequence, id_pai, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """

        conn = self._get_thread_connection()
        try:
            with conn:
                conn.executemany(insert_query, valid_rows)
            print(f"{len(valid_rows)} produtos inseridos na base de dados (substituição completa com relação pai-filho).")
            return len(valid_rows)
        except sqlite3.Error as e:
            print(f"ERRO DB (replace_all_tiny_products): {e}")
            return 0
        
    def upsert_tiny_products(self, df: pd.DataFrame) -> tuple[int, int]:
        """Adiciona ou atualiza produtos Tiny a partir de um DataFrame (baseado no SKU)."""
        
        # <<<<<<<<<<<<<<<< ADICIONADO `url_imagem_1` À QUERY >>>>>>>>>>>>>>>>>>
        query = """
            INSERT INTO tiny_products (
                id_produto, sku, descricao, peso, largura, altura, profundidade, stock, 
                curva_a_posicao, curva_a_rank, url_imagem_1, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(sku) DO UPDATE SET
                id_produto = excluded.id_produto,
                descricao = excluded.descricao,
                peso = excluded.peso,
                largura = excluded.largura,
                altura = excluded.altura,
                profundidade = excluded.profundidade,
                stock = excluded.stock,
                curva_a_posicao = excluded.curva_a_posicao,
                curva_a_rank = excluded.curva_a_rank,
                url_imagem_1 = excluded.url_imagem_1,
                atualizado_em = CURRENT_TIMESTAMP
        """
        # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< FIM DA ADIÇÃO >>>>>>>>>>>>>>>>>>>>>>>>
        
        updated_count = 0
        inserted_count = 0
        
        conn = self._get_thread_connection()
        try:
            with conn:
                for _, row in df.iterrows():
                    sku = str(row['Código (SKU)']).strip() if 'Código (SKU)' in row and pd.notna(row['Código (SKU)']) else None
                    if not sku:
                        continue

                    cursor = conn.cursor()
                    cursor.execute("SELECT 1 FROM tiny_products WHERE sku = ?", (sku,))
                    exists = cursor.fetchone()
                    
                    params = (
                        row.get('ID', None), sku, row.get('Descrição', ''),
                        float(row.get('Peso bruto (Kg)', 0) or 0),
                        float(row.get('Largura embalagem', 0) or 0),
                        float(row.get('Altura embalagem', 0) or 0),
                        float(row.get('Comprimento embalagem', 0) or 0),
                        float(row.get('Estoque', 0) or 0),
                        row.get('Classificação', None),
                        int(row.get('Rank', 9999)) if pd.notna(row.get('Rank')) else 9999,
                        row.get('URL imagem 1', None) # <<<<<<<<<<<<<<< ADICIONADO
                    )
                    
                    cursor.execute(query, params)
                    
                    if exists:
                        updated_count += 1
                    else:
                        inserted_count += 1
            return updated_count, inserted_count
        except sqlite3.Error as e:
            print(f"ERRO DB (upsert_tiny_products): {e}")
            return 0, 0


    def save_or_update_tiny_product(self, product_data):
        """Salva ou atualiza um único produto Tiny na tabela tiny_products."""
        query = """
            INSERT INTO tiny_products (
                id_produto, sku, descricao, peso, largura, altura, profundidade, status, stock, id_pai, atualizado_em
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(sku) DO UPDATE SET
                id_produto = excluded.id_produto,
                descricao = excluded.descricao,
                peso = excluded.peso,
                largura = excluded.largura,
                altura = excluded.altura,
                profundidade = excluded.profundidade,
                status = excluded.status,
                stock = excluded.stock,
                id_pai = excluded.id_pai,
                atualizado_em = CURRENT_TIMESTAMP;
        """
        params = (
            product_data.get('id_produto'),
            product_data.get('sku'),
            product_data.get('descricao'),
            product_data.get('peso'),
            product_data.get('largura'),
            product_data.get('altura'),
            product_data.get('profundidade'),
            product_data.get('status'),
            product_data.get('stock'),
            product_data.get('id_pai')
        )
        self._execute_query(query, params, commit=True)

    def get_all_tiny_products(self):
        """
        Busca todos os produtos da tabela tiny_products,
        ordenando pela ordem da planilha (import_sequence) primeiro,
        e colocando produtos não classificados no final.
        """
        # Esta query é a chave da solução:
        # 1. CASE WHEN import_sequence IS NULL THEN 1 ELSE 0 END: Cria um "grupo de ordenação".
        #    - Produtos com sequência (da planilha ABC) ficam no grupo 0.
        #    - Produtos sem sequência (NULL) ficam no grupo 1.
        #    A ordenação por este CASE coloca o grupo 0 antes do grupo 1.
        # 2. import_sequence ASC: Dentro do grupo 0, ordena pela sequência da planilha.
        # 3. sku ASC: Dentro do grupo 1 (dos não ordenados), ordena alfabeticamente por SKU.
        query = """
            SELECT *
              FROM tiny_products
             ORDER BY CASE WHEN import_sequence IS NULL THEN 1 ELSE 0 END, 
                      import_sequence ASC,
                      sku ASC
        """
        rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def update_product_abc_position(self, sku, classification, rank, sequence):
        """
        Atualiza a posição, o rank e a sequência de importação da curva ABC
        para um SKU específico.
        """
        query = """
        UPDATE tiny_products
           SET curva_a_posicao   = ?,
               curva_a_rank      = ?,
               import_sequence   = ?
         WHERE sku = ?
        """
        # sequence é o índice da linha (idx) no DataFrame
        self._execute_query(query, (classification, rank, sequence, sku), commit=True)
            
    def add_item_to_promo_queue(self, account_nickname, promotion_id, promotion_type, items_payload, extra_data):
        """[UNIFICADO] Adiciona uma tarefa de Ativação de Promoção."""
        payload = {
            "promotion_id": promotion_id,
            "promotion_type": promotion_type,
            "items_payload": items_payload,
            "extra_data": extra_data
        }
        # item_id não é relevante no nível da tarefa, mas nos itens do payload.
        return self.add_task_to_queue("PROMO_ACTIVATION", account_nickname, item_id=promotion_id, payload=payload)

            
    def _get_thread_connection(self):
        if not hasattr(self.thread_local, 'conn') or self.thread_local.conn is None:
            try:
                conn = sqlite3.connect(self.db_name, timeout=10, check_same_thread=False)
                conn.row_factory = sqlite3.Row
                conn.execute("PRAGMA foreign_keys = ON;")
                conn.execute("PRAGMA journal_mode=WAL;")
                self.thread_local.conn = conn
            except sqlite3.Error as e:
                print(f"DB: Thread {threading.get_ident()} FAILED to create connection: {e}")
                self.thread_local.conn = None
                raise
        return self.thread_local.conn

    # --- Compatibility Profiles DB Methods ---
    def save_compatibility_profile_to_db(self, profile_name: str, compatibilities_list: list, description: str = ""):
        """Saves or updates a compatibility profile in the database."""
        if not profile_name or not isinstance(compatibilities_list, list):
            print("DB Save Compat Profile: Nome do perfil ou lista de compatibilidades inválida.")
            return False
        
        compat_json_str = json.dumps(compatibilities_list)
        query = """
            INSERT INTO compatibility_profiles_db (profile_name, compatibilities_json, description, created_at, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT(profile_name) DO UPDATE SET
                compatibilities_json = excluded.compatibilities_json,
                description = excluded.description,
                updated_at = CURRENT_TIMESTAMP;
        """
        try:
            self._execute_query(query, (profile_name, compat_json_str, description), commit=True)
            print(f"DB: Perfil de compatibilidade '{profile_name}' salvo/atualizado.")
            return True
        except Exception as e:
            print(f"DB: Erro ao salvar perfil de compatibilidade '{profile_name}': {e}")
            return False

    def load_compatibility_profile_from_db(self, profile_name: str) -> dict | None:
        """Loads a specific compatibility profile from the database. Returns the profile data as a dict."""
        row = self._execute_query(
            "SELECT profile_name, compatibilities_json, description, created_at, updated_at FROM compatibility_profiles_db WHERE profile_name = ?",
            (profile_name,),
            fetch_one=True
        )
        if row:
            try:
                compat_list = json.loads(row['compatibilities_json'])
                return {
                    "profile_name": row['profile_name'],
                    "compatibilities_list": compat_list,
                    "description": row['description'],
                    "created_at": row['created_at'],
                    "updated_at": row['updated_at']
                }
            except json.JSONDecodeError as e:
                print(f"DB: Erro ao decodificar JSON do perfil de compatibilidade '{profile_name}': {e}")
                return None
        return None

    def load_all_compatibility_profile_names_from_db(self) -> list[str]:
        """Loads all compatibility profile names from the database."""
        rows = self._execute_query("SELECT profile_name FROM compatibility_profiles_db ORDER BY profile_name ASC", fetch_all=True)
        if rows:
            return [row['profile_name'] for row in rows]
        return []

    def delete_compatibility_profile_from_db(self, profile_name: str) -> bool:
        """Deletes a compatibility profile from the database by name."""
        if not profile_name:
            return False
        try:
            self._execute_query("DELETE FROM compatibility_profiles_db WHERE profile_name = ?", (profile_name,), commit=True)
            print(f"DB: Perfil de compatibilidade '{profile_name}' deletado.")
            return True
        except Exception as e:
            print(f"DB: Erro ao deletar perfil de compatibilidade '{profile_name}': {e}")
            return False

    def _close_thread_connection(self, force_close=False):
        """Closes the connection for the current thread if it exists."""
        if hasattr(self.thread_local, 'conn') and self.thread_local.conn is not None:
            self.thread_local.conn.close()
            self.thread_local.conn = None

    def close_all_connections_for_app_exit(self): 
        """Intended to be called when the application is shutting down."""
        print("DatabaseManager: Attempting to close main thread's connection (if any).")
        self._close_thread_connection(force_close=True)

    def _execute_query(self, query, params=(), commit=False, fetch_one=False, fetch_all=False):
        conn = self._get_thread_connection()
        if not conn: return None
        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            if commit: conn.commit()
            if fetch_one: return cursor.fetchone()
            if fetch_all: return cursor.fetchall()
            return cursor
        except sqlite3.Error as e_query:
            error_msg = f"SQLite error: {e_query}\nQuery: {query}\nParams: {params}"
            print(error_msg)
            if conn and conn.in_transaction:
                try: conn.rollback()
                except sqlite3.Error as rb_err: print(f"Error during rollback: {rb_err}")
            return None
        finally:
            if cursor:
                try: cursor.close()
                except sqlite3.Error: pass

    def add_item_to_ad_fetch_queue(self, account_nickname, payload_dict):
        """[UNIFICADO] Adiciona uma tarefa de Busca de Anúncios."""
        # A tarefa de busca é por conta, então item_id é N/A
        return self.add_task_to_queue("AD_FETCH", account_nickname, item_id=None, payload=payload_dict)


# DENTRO DA CLASSE DatabaseManager
# SUBSTITUA ESTE MÉTODO INTEIRO PELA VERSÃO FINAL E CORRIGIDA

    def _create_tables_with_cursor(self, cursor):
        """[VERSÃO FINAL E CORRIGIDA] Cria/migra todas as tabelas, colunas, índices e gatilhos na ordem correta."""
        import re
        
        # --- ETAPA 1: CRIAR TABELAS ---
        # Esta parte cria as tabelas apenas se elas não existirem.
        queries = [
            """
            CREATE TABLE IF NOT EXISTS unified_task_queue (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT, task_type TEXT NOT NULL, item_id TEXT,
                account_nickname TEXT NOT NULL, status TEXT DEFAULT 'PENDING', payload_json TEXT,
                retry_count INTEGER DEFAULT 0, last_error_message TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS catalog_rejections (
                item_id TEXT NOT NULL,
                catalog_product_id TEXT NOT NULL,
                reason TEXT,
                rejected_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (item_id, catalog_product_id)
            )
            """,
            "CREATE TABLE IF NOT EXISTS ml_parent_items (item_id TEXT PRIMARY KEY, account_nickname TEXT NOT NULL, title TEXT, category_id TEXT, last_sync DATETIME DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS ml_variations (variation_id INTEGER PRIMARY KEY, parent_item_id TEXT NOT NULL, seller_sku TEXT NOT NULL, attributes_json TEXT, tiny_sku TEXT, UNIQUE(parent_item_id, seller_sku), FOREIGN KEY (parent_item_id) REFERENCES ml_parent_items (item_id) ON DELETE CASCADE)",
            """
            CREATE TABLE IF NOT EXISTS ml_accounts (
                nickname TEXT PRIMARY KEY, access_token TEXT, refresh_token TEXT, 
                expires_at INTEGER, seller_id TEXT, user_id_from_token TEXT, 
                shipping_mode TEXT, seller_reputation TEXT, power_seller_status TEXT, 
                official_store_id INTEGER, can_create_promotions INTEGER DEFAULT 1, 
                shipping_type TEXT DEFAULT 'me2_traditional', tags TEXT
            )
            """,
            "CREATE TABLE IF NOT EXISTS fixed_prices (sku TEXT PRIMARY KEY, price REAL, notes TEXT)",
            "CREATE TABLE IF NOT EXISTS modified_ads_history (item_id TEXT PRIMARY KEY, account_nickname TEXT, timestamp DATETIME)",
            "CREATE TABLE IF NOT EXISTS promotions_cache (account_nickname TEXT PRIMARY KEY, promotions_json TEXT, last_updated DATETIME)",
            "CREATE TABLE IF NOT EXISTS app_config (key TEXT PRIMARY KEY, value_type TEXT, value TEXT)",
            "CREATE TABLE IF NOT EXISTS compatibility_profiles_db (profile_name TEXT PRIMARY KEY, compatibilities_json TEXT, description TEXT, created_at DATETIME, updated_at DATETIME)",
            "CREATE TABLE IF NOT EXISTS promo_exclusions (exclusion_type TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY (exclusion_type, value))",
            "CREATE TABLE IF NOT EXISTS sku_processed_images (sku TEXT NOT NULL, image_url TEXT NOT NULL, added_timestamp DATETIME, PRIMARY KEY (sku, image_url))",
            # <<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA MODIFICAÇÃO >>>>>>>>>>>>>>>>>>>>
            "CREATE TABLE IF NOT EXISTS tiny_products (id_produto INTEGER, sku TEXT PRIMARY KEY, descricao TEXT, peso REAL, largura REAL, altura REAL, profundidade REAL, stock REAL, status TEXT DEFAULT 'A', curva_a_posicao TEXT, curva_a_rank INTEGER, url_imagem_1 TEXT, import_sequence INTEGER, atualizado_em DATETIME, vendas_qtd REAL DEFAULT 0, vendas_valor REAL DEFAULT 0, id_pai INTEGER)",
            # <<<<<<<<<<<<<<<<<<<<<<<<< FIM DA MODIFICAÇÃO >>>>>>>>>>>>>>>>>>>>>
            "CREATE TABLE IF NOT EXISTS product_groups (group_id INTEGER PRIMARY KEY AUTOINCREMENT, group_name TEXT NOT NULL UNIQUE, description TEXT)",
            "CREATE TABLE IF NOT EXISTS product_group_skus (group_id INTEGER NOT NULL, sku TEXT NOT NULL, PRIMARY KEY (group_id, sku), FOREIGN KEY (group_id) REFERENCES product_groups (group_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS competitor_ads (competitor_ad_id INTEGER PRIMARY KEY AUTOINCREMENT, mlb_id TEXT NOT NULL UNIQUE, linked_group_id INTEGER NOT NULL, parent_sku TEXT NOT NULL, url TEXT NOT NULL, last_known_title TEXT, last_known_price REAL, last_known_stock INTEGER, last_updated TEXT, FOREIGN KEY (linked_group_id) REFERENCES product_groups (group_id) ON DELETE CASCADE)",
            "CREATE TABLE IF NOT EXISTS pricing_rules (rule_id INTEGER PRIMARY KEY AUTOINCREMENT, rule_name TEXT NOT NULL UNIQUE, account_nickname TEXT NOT NULL, listing_type TEXT NOT NULL, price_threshold REAL NOT NULL, comparison_operator TEXT NOT NULL, base_price_source TEXT NOT NULL DEFAULT 'tiny_price', fixed_value_add REAL NOT NULL DEFAULT 0.0, percentage_markup REAL NOT NULL DEFAULT 0.0, fixed_value_discount REAL NOT NULL DEFAULT 0.0, percentage_discount REAL NOT NULL DEFAULT 0.0, include_shipping_cost INTEGER NOT NULL DEFAULT 0, description TEXT)",
            # --- Tabelas da Aba 18 (Qualidade) ---
            """
            CREATE TABLE IF NOT EXISTS quality_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_nick TEXT NOT NULL,
                item_id TEXT NOT NULL,
                sku TEXT,
                category_id TEXT,
                domain_id TEXT,
                has_catalog INTEGER,
                health REAL,
                tech_score INTEGER,
                missing_attr_ids TEXT,
                source TEXT,                         -- 'aba8' | 'scan18'
                status TEXT DEFAULT 'pending',       -- 'pending' | 'fixed' | 'error'
                last_checked_at TEXT,
                last_error TEXT,
                UNIQUE(item_id, account_nick) ON CONFLICT REPLACE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS quality_audit (
                ts TEXT DEFAULT CURRENT_TIMESTAMP,
                user TEXT,
                account_nick TEXT,
                item_id TEXT,
                sku TEXT,
                payload_json TEXT,
                http_status INTEGER,
                response_json TEXT
            )
            """,


        ]
        for query in queries:
            try:
                cursor.execute(query)
            except sqlite3.Error as e:
                raise sqlite3.Error(f"Falha ao criar tabela: {e}")
        print("DB Init: Todas as tabelas verificadas/criadas.")

        # --- ETAPA 2: MIGRAÇÃO E VERIFICAÇÃO DE COLUNAS ---
        # Esta parte garante que as colunas existam, mesmo em um DB antigo.
        try:
            print("DB Init: Verificando/Adicionando colunas na 'unified_task_queue'...")
            info = cursor.execute("PRAGMA table_info(unified_task_queue)").fetchall()
            existing_cols = {row[1] for row in info}
            
            required_columns = {
                "added_timestamp": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "updated_timestamp": "DATETIME DEFAULT CURRENT_TIMESTAMP",
                "scheduled_for": "DATETIME"
            }

            for col_name, col_definition in required_columns.items():
                if col_name not in existing_cols:
                    print(f"  -> Adicionando coluna ausente: '{col_name}'...")
                    cursor.execute(f"ALTER TABLE unified_task_queue ADD COLUMN {col_name} {col_definition}")
                    # Preenche valores nulos na nova coluna para evitar problemas com o gatilho
                    if col_name in ("added_timestamp", "updated_timestamp"):
                        cursor.execute(f"UPDATE unified_task_queue SET {col_name} = CURRENT_TIMESTAMP WHERE {col_name} IS NULL")
                    print(f"  -> Coluna '{col_name}' adicionada com sucesso.")
            
            print("DB Init: Verificação de colunas concluída.")
        except sqlite3.Error as e:
            print(f"SQLite migration warning (unified_task_queue): {e}")

        # <<<<<<<<<<<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>
        # Migração para 'tiny_products'
        try:
            info_tiny = cursor.execute("PRAGMA table_info(tiny_products)").fetchall()
            existing_cols_tiny = {row[1] for row in info_tiny}
            required_cols_tiny = {"vendas_qtd": "REAL DEFAULT 0", "vendas_valor": "REAL DEFAULT 0", "id_pai": "INTEGER"}
            
            for col, definition in required_cols_tiny.items():
                if col not in existing_cols_tiny:
                    print(f"  -> Migrando DB: Adicionando coluna '{col}' à 'tiny_products'...")
                    cursor.execute(f"ALTER TABLE tiny_products ADD COLUMN {col} {definition}")
            print("DB Init: Verificação de colunas da 'tiny_products' concluída.")
        except sqlite3.Error as e:
            print(f"SQLite migration warning (tiny_products): {e}")
        # <<<<<<<<<<<<<<<<<<<<<<<<< FIM DA CORREÇÃO >>>>>>>>>>>>>>>>>>>>>

        # --- ETAPA 3: CRIAR ÍNDICES ---
        try:
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_unified_queue_status ON unified_task_queue(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_unified_queue_tasktype ON unified_task_queue(task_type)")
            print("DB Init: Índices da fila verificados/criados.")
        except sqlite3.Error:
            pass

        # --- ETAPA 4: CRIAR GATILHOS (APÓS GARANTIR QUE AS COLUNAS EXISTEM) ---
        # Sempre remove os gatilhos antigos antes de criar os novos.
        cursor.execute("DROP TRIGGER IF EXISTS update_compat_profile_db_updated_at;")
        cursor.execute("DROP TRIGGER IF EXISTS unified_queue_update_timestamp;")

        trigger_queries = [
            """
            CREATE TRIGGER update_compat_profile_db_updated_at
            AFTER UPDATE ON compatibility_profiles_db FOR EACH ROW
            BEGIN
                UPDATE compatibility_profiles_db SET updated_at = CURRENT_TIMESTAMP WHERE profile_name = OLD.profile_name;
            END;
            """,
            """
            CREATE TRIGGER unified_queue_update_timestamp
            AFTER UPDATE ON unified_task_queue FOR EACH ROW
            BEGIN
                UPDATE unified_task_queue SET updated_timestamp = CURRENT_TIMESTAMP WHERE task_id = OLD.task_id;
            END;
            """
        ]
        for trigger_query in trigger_queries:
            cursor.execute(trigger_query)
        
        print("DB Init: Gatilhos do banco de dados verificados/recriados.")

    def add_catalog_rejection(self, item_id: str, catalog_product_id: str, reason: str = ""):
        """Salva a recusa de um item para um catálogo específico."""
        query = "INSERT OR REPLACE INTO catalog_rejections (item_id, catalog_product_id, reason) VALUES (?, ?, ?)"
        self._execute_query(query, (item_id, catalog_product_id, reason), commit=True)
        print(f"DB: Rejeição do item {item_id} para o catálogo {catalog_product_id} foi registrada.")

    def is_catalog_rejection_registered(self, item_id: str, catalog_product_id: str) -> bool:
        """Verifica se uma recusa específica já foi registrada."""
        query = "SELECT 1 FROM catalog_rejections WHERE item_id = ? AND catalog_product_id = ?"
        result = self._execute_query(query, (item_id, catalog_product_id), fetch_one=True)
        return result is not None


    def save_parent_item_with_variations(self, parent_data, variations_data):
        """
        Salva um item pai e suas variações de forma transacional.
        :param parent_data: Dict com chaves 'item_id', 'account_nickname', 'title', 'category_id'.
        :param variations_data: Lista de dicts, cada um com 'variation_id', 'parent_item_id', 'seller_sku', 'attributes_json'.
        """
        conn = self._get_thread_connection()
        try:
            with conn: # Inicia uma transação
                cursor = conn.cursor()
                
                # Insere ou substitui o item pai
                cursor.execute(
                    "INSERT OR REPLACE INTO ml_parent_items (item_id, account_nickname, title, category_id) VALUES (?, ?, ?, ?)",
                    (parent_data['item_id'], parent_data['account_nickname'], parent_data['title'], parent_data['category_id'])
                )
                
                # Insere ou substitui as variações
                if variations_data:
                    variations_to_upsert = [
                        (v['variation_id'], v['parent_item_id'], v['seller_sku'], v['attributes_json'])
                        for v in variations_data
                    ]
                    cursor.executemany(
                        """
                        INSERT OR REPLACE INTO ml_variations (variation_id, parent_item_id, seller_sku, attributes_json)
                        VALUES (?, ?, ?, ?)
                        """,
                        variations_to_upsert
                    )
            print(f"DB: Item pai {parent_data['item_id']} e {len(variations_data)} variações salvos/atualizados.")
            return True
        except sqlite3.Error as e:
            print(f"DB ERRO ao salvar item com variações: {e}")
            return False

    def get_variation_info_by_sku(self, sku: str, account_nickname: str) -> dict | None:
        """
        Busca o parent_item_id e variation_id de um SKU específico em uma conta.
        Retorna um dicionário com os IDs ou None se não encontrado.
        """
        query = """
            SELECT v.parent_item_id, v.variation_id
            FROM ml_variations v
            JOIN ml_parent_items p ON v.parent_item_id = p.item_id
            WHERE v.seller_sku = ? AND p.account_nickname = ?
        """
        row = self._execute_query(query, (sku, account_nickname), fetch_one=True)
        return dict(row) if row else None

    def get_variations_for_parent(self, parent_item_id: str) -> list[dict]:
        """Retorna todas as variações (filhos) de um item pai."""
        query = "SELECT * FROM ml_variations WHERE parent_item_id = ?"
        rows = self._execute_query(query, (parent_item_id,), fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def add_item_to_price_check_queue(self, item_id, account_nickname, rules_payload):
        """[UNIFICADO] Adiciona uma tarefa de Verificação de Preço."""
        return self.add_task_to_queue("PRICE_CHECK", account_nickname, item_id, rules_payload)

    # DENTRO DA CLASSE DatabaseManager
    # SUBSTITUA ESTE MÉTODO INTEIRO

    def get_all_price_check_statuses(self) -> dict:
        """
        [CORRIGIDO] Busca o status MAIS RECENTE para CADA item_id na fila de verificação de preço.
        Retorna um dicionário mapeando item_id para seu status e resultado.
        Ex: {'MLB123': {'status': 'DONE', 'result': 'OK'}, 'MLB456': {'status': 'PENDING', 'result': None}}
        """
        query = """
            WITH LatestTasks AS (
                SELECT 
                    item_id, 
                    status, 
                    last_error_message,
                    ROW_NUMBER() OVER(PARTITION BY item_id ORDER BY added_timestamp DESC) as rn
                FROM 
                    unified_task_queue
                WHERE 
                    task_type = 'PRICE_CHECK' AND item_id IS NOT NULL
            )
            SELECT 
                item_id, 
                status, 
                last_error_message
            FROM 
                LatestTasks
            WHERE 
                rn = 1;
        """
        rows = self._execute_query(query, fetch_all=True)
        status_map = {}
        if rows:
            for row in rows:
                status_map[row['item_id']] = {
                    'status': row['status'],
                    'result': row['last_error_message']
                }
        return status_map

    def save_pricing_rule(self, rule_data):
        """Salva ou atualiza uma regra de precificação no banco de dados."""
        is_update = 'rule_id' in rule_data and rule_data['rule_id'] is not None
        
        if is_update:
            query = """
                UPDATE pricing_rules SET
                    rule_name = :rule_name, account_nickname = :account_nickname,
                    listing_type = :listing_type, price_threshold = :price_threshold,
                    comparison_operator = :comparison_operator, base_price_source = :base_price_source,
                    fixed_value_add = :fixed_value_add, percentage_markup = :percentage_markup,
                    include_shipping_cost = :include_shipping_cost, description = :description,
                    fixed_value_discount = :fixed_value_discount, percentage_discount = :percentage_discount
                WHERE rule_id = :rule_id
            """
        else:
            query = """
                INSERT INTO pricing_rules (
                    rule_name, account_nickname, listing_type, price_threshold,
                    comparison_operator, base_price_source, fixed_value_add,
                    percentage_markup, include_shipping_cost, description,
                    fixed_value_discount, percentage_discount
                ) VALUES (
                    :rule_name, :account_nickname, :listing_type, :price_threshold,
                    :comparison_operator, :base_price_source, :fixed_value_add,
                    :percentage_markup, :include_shipping_cost, :description,
                    :fixed_value_discount, :percentage_discount
                )
            """
        
        try:
            self._execute_query(query, rule_data, commit=True)
            return True, "Regra salva com sucesso."
        except sqlite3.IntegrityError:
            return False, "Já existe uma regra com este nome."
        except Exception as e:
            return False, f"Erro no banco de dados: {e}"

    def get_all_pricing_rules(self):
        """Busca todas as regras de precificação, ordenadas por nome."""
        query = "SELECT * FROM pricing_rules ORDER BY rule_name ASC"
        rows = self._execute_query(query, fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def delete_pricing_rule(self, rule_id):
        """Deleta uma regra de precificação pelo seu ID."""
        self._execute_query("DELETE FROM pricing_rules WHERE rule_id = ?", (rule_id,), commit=True)


    def save_ml_account(self, nickname, data_dict):
        """Saves or updates an ML account in the database."""
        seller_rep_json = json.dumps(data_dict.get('seller_reputation')) if isinstance(data_dict.get('seller_reputation'), dict) else None
        can_create_promos_val = 1 if data_dict.get('can_create_promotions', True) else 0
        shipping_type_val = data_dict.get('shipping_type', 'me2_traditional') # Default para tradicional
        tags_json = json.dumps(data_dict.get('tags', [])) # Converte a lista de tags para JSON, com fallback para lista vazia

        params = (
            nickname, data_dict.get('access_token'), data_dict.get('refresh_token'),
            int(data_dict.get('expires_at', 0)), data_dict.get('seller_id'),
            data_dict.get('user_id_from_token'), data_dict.get('shipping_mode', 'me2'),
            shipping_type_val,
            seller_rep_json, data_dict.get('power_seller_status'), data_dict.get('official_store_id'),
            can_create_promos_val,
            tags_json # Adiciona o novo parâmetro
        )
        query = """
            INSERT OR REPLACE INTO ml_accounts 
            (nickname, access_token, refresh_token, expires_at, seller_id, 
            user_id_from_token, shipping_mode, shipping_type, seller_reputation, power_seller_status, 
            official_store_id, can_create_promotions, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_query(query, params, commit=True)


    def load_all_ml_accounts(self):
        """Loads all ML accounts from the database, ensuring IDs are strings and flags are boolean."""
        accounts = {}
        rows = self._execute_query("SELECT * FROM ml_accounts", fetch_all=True)
        if rows:
            for row_data_obj in rows:
                account_dict = dict(row_data_obj) 
                
                if account_dict.get('seller_id') is not None:
                    account_dict['seller_id'] = str(account_dict['seller_id'])
                if account_dict.get('user_id_from_token') is not None:
                    account_dict['user_id_from_token'] = str(account_dict['user_id_from_token'])
                
                if 'shipping_type' not in account_dict or not account_dict['shipping_type']:
                    account_dict['shipping_type'] = 'me2_traditional'

                account_dict['can_create_promotions'] = bool(account_dict.get('can_create_promotions', 1))

                # Lógica para seller_reputation
                if account_dict.get('seller_reputation'):
                    try:
                        loaded_rep = json.loads(account_dict['seller_reputation'])
                        account_dict['seller_reputation'] = loaded_rep if isinstance(loaded_rep, dict) else None
                    except (json.JSONDecodeError, TypeError):
                        account_dict['seller_reputation'] = None 
                else:
                    account_dict['seller_reputation'] = None
                
                # <<<<<<<<<<<<<<< INÍCIO DA CORREÇÃO >>>>>>>>>>>>>>>>
                # Garante que 'tags' seja sempre uma lista, nunca None.
                tags_from_db = account_dict.get('tags')
                if isinstance(tags_from_db, str) and tags_from_db:
                    try:
                        parsed_tags = json.loads(tags_from_db)
                        account_dict['tags'] = parsed_tags if isinstance(parsed_tags, list) else []
                    except json.JSONDecodeError:
                        account_dict['tags'] = []
                else: # Se for None, vazio, ou outro tipo
                    account_dict['tags'] = []
                # <<<<<<<<<<<<<<<< FIM DA CORREÇÃO >>>>>>>>>>>>>>>>>
                
                accounts[account_dict['nickname']] = account_dict
        return accounts
    
    def delete_ml_account(self, nickname):
        """Deletes an ML account from the database by nickname."""
        self._execute_query("DELETE FROM ml_accounts WHERE nickname = ?", (nickname,), commit=True)
    
    # --- Fixed Price DB Methods ---
    def save_fixed_price(self, sku: str, price: float, notes: str = ""):
        query = "INSERT OR REPLACE INTO fixed_prices (sku, price, notes) VALUES (?, ?, ?)"
        self._execute_query(query, (sku.strip().upper(), price, notes), commit=True)

    def delete_fixed_price(self, sku: str):
        query = "DELETE FROM fixed_prices WHERE sku = ?"
        self._execute_query(query, (sku.strip().upper(),), commit=True)

    def get_all_fixed_prices(self) -> dict:
        """Loads all fixed prices into a dictionary {sku: price} for quick lookups."""
        query = "SELECT sku, price FROM fixed_prices"
        rows = self._execute_query(query, fetch_all=True)
        return {row['sku']: row['price'] for row in rows} if rows else {}


    # --- Modified Ads History DB Methods ---
    def add_item_to_history(self, item_id: str, account_nickname: str):
        """Adds or replaces an item in the modification history."""
        query = "INSERT OR REPLACE INTO modified_ads_history (item_id, account_nickname, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)"
        self._execute_query(query, (item_id, account_nickname), commit=True)

    def get_all_history_items(self) -> list[dict]:
        """Gets all items from the modification history."""
        rows = self._execute_query("SELECT item_id, account_nickname FROM modified_ads_history", fetch_all=True)
        return [dict(row) for row in rows] if rows else []

    def clear_history(self):
        """Deletes all records from the modification history."""
        self._execute_query("DELETE FROM modified_ads_history", commit=True)
        print("DB: Tabela de histórico de modificações limpa.")

    def _create_tables(self):
        """Creates all necessary tables in the database if they don't already exist."""
        # Este método parece um duplicado de _create_tables_with_cursor. Manteremos o outro.
        pass

    # --- Promotions Cache DB Methods ---
    def save_promotions_to_cache(self, account_nickname: str, promotions_list: list):
        """Salva a lista de promoções de uma conta no cache do DB."""
        if not account_nickname or not isinstance(promotions_list, list):
            return
        promotions_json = json.dumps(promotions_list)
        query = """
            INSERT OR REPLACE INTO promotions_cache (account_nickname, promotions_json, last_updated)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """
        self._execute_query(query, (account_nickname, promotions_json), commit=True)
        print(f"DB Cache: Promoções para '{account_nickname}' salvas no cache.")

    def load_promotions_from_cache(self, account_nickname: str) -> tuple[list | None, str | None]:
        """Carrega a lista de promoções de uma conta do cache do DB."""
        row = self._execute_query(
            "SELECT promotions_json, last_updated FROM promotions_cache WHERE account_nickname = ?",
            (account_nickname,),
            fetch_one=True
        )
        if row:
            try:
                promo_list = json.loads(row['promotions_json'])
                last_updated = row['last_updated']
                return promo_list, last_updated
            except (json.JSONDecodeError, TypeError) as e:
                print(f"DB Cache: Erro ao carregar/decodificar cache de promoções para '{account_nickname}': {e}")
                return None, None
        return None, None

    def load_all_promotions_from_cache(self) -> dict:
        """Carrega todo o cache de promoções de todas as contas na inicialização."""
        all_promos_cache = {}
        rows = self._execute_query("SELECT account_nickname, promotions_json FROM promotions_cache", fetch_all=True)
        if rows:
            for row in rows:
                try:
                    all_promos_cache[row['account_nickname']] = json.loads(row['promotions_json'])
                except (json.JSONDecodeError, TypeError):
                    continue # Ignora cache corrompido para uma conta
        print(f"DB Cache: Carregado cache de promoções para {len(all_promos_cache)} contas.")
        return all_promos_cache

    def get_app_config_value(self, key, default_value_if_not_found=None):
        """Retrieves a configuration value, parsing it to its original Python type."""
        row = self._execute_query("SELECT value, value_type FROM app_config WHERE key = ?", (key,), fetch_one=True)
        if row and row['value'] is not None: 
            value_str = row['value']
            value_type = row['value_type']
            try:
                if value_type == 'none': return None 
                if value_type == 'int': return int(value_str)
                if value_type == 'float': return float(value_str)
                if value_type == 'bool': return value_str.lower() == 'true' or value_str == '1'
                if value_type == 'json_list': return json.loads(value_str) if value_str else []
                if value_type == 'json_dict': return json.loads(value_str) if value_str else {}
                return value_str
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                print(f"Error parsing stored config value for key '{key}' (expected type: {value_type}, stored value: '{value_str}'): {e}. Returning provided default.")
                return default_value_if_not_found
        elif row and row['value'] is None and row['value_type'] == 'none': 
             return None
        return default_value_if_not_found

    def set_app_config_value(self, key, value):
        """Saves a configuration value, determining its type for storage."""
        value_type = 'str' 
        value_to_save = str(value)

        if value is None: value_type = 'none'; value_to_save = None 
        elif isinstance(value, bool): value_type = 'bool'; value_to_save = 'true' if value else 'false'
        elif isinstance(value, int): value_type = 'int' 
        elif isinstance(value, float): value_type = 'float' 
        elif isinstance(value, list): value_type = 'json_list'; value_to_save = json.dumps(value)
        elif isinstance(value, dict): value_type = 'json_dict'; value_to_save = json.dumps(value)
        
        self._execute_query(
            "INSERT OR REPLACE INTO app_config (key, value_type, value) VALUES (?, ?, ?)",
            (key, value_type, value_to_save), 
            commit=True
        )

    def load_all_app_config(self, default_config_structure_dict):
        """Loads all configuration values, using defaults and saving them if keys are missing in DB."""
        config_from_db = {}
        for def_key, def_value_example in default_config_structure_dict.items():
            val_from_db = self.get_app_config_value(def_key, default_value_if_not_found=object()) 
            
            if val_from_db is object(): 
                config_from_db[def_key] = def_value_example
                self.set_app_config_value(def_key, def_value_example)
            else: 
                config_from_db[def_key] = val_from_db
        return config_from_db
        

    def add_item_to_bulk_queue(self, item_id, account_nickname, actions_payload, original_item_data):
        """[UNIFICADO] Adiciona uma tarefa de Edição em Massa."""
        payload = {
            "actions_to_perform": actions_payload,
            "original_item_data": original_item_data
        }
        return self.add_task_to_queue("BULK_EDIT", account_nickname, item_id, payload)


    def get_bulk_queue_items_by_ids(self, task_ids: list):
        """Busca itens específicos da fila por seus task_ids."""
        if not task_ids: return []
        placeholders = ','.join('?' for _ in task_ids)
        query = f"SELECT * FROM bulk_edit_queue WHERE task_id IN ({placeholders})"
        rows = self._execute_query(query, tuple(task_ids), fetch_all=True)
        return [dict(row) for row in rows] if rows else []


    def save_promo_exclusions(self, exclusions_data_dict):
        """Saves promotion exclusions, clearing old ones first."""
        self._execute_query("DELETE FROM promo_exclusions", commit=True)
        
        conn = self._get_thread_connection()
        if not conn:
            print("DB ERROR: Não foi possível obter conexão para salvar exclusões de promoção.")
            return

        mlbs = exclusions_data_dict.get("excluded_mlbs", [])
        skus = exclusions_data_dict.get("excluded_skus", [])
        
        try:
            if mlbs:
                mlb_params = [('mlb', mlb_id) for mlb_id in mlbs if mlb_id] 
                if mlb_params:
                    conn.executemany("INSERT OR IGNORE INTO promo_exclusions (exclusion_type, value) VALUES (?, ?)", mlb_params)
            if skus:
                sku_params = [('sku', sku) for sku in skus if sku] 
                if sku_params:
                    conn.executemany("INSERT OR IGNORE INTO promo_exclusions (exclusion_type, value) VALUES (?, ?)", sku_params)
            
            conn.commit()
            
        except sqlite3.Error as e:
            print(f"DB: Erro durante executemany em save_promo_exclusions: {e}")
            try:
                conn.rollback() 
                print("DB: Transação revertida para promo_exclusions.")
            except sqlite3.Error as rb_err:
                print(f"DB: Erro durante a tentativa de rollback: {rb_err}")

    def load_promo_exclusions(self):
        """Loads all promotion exclusions from the database."""
        exclusions = {"excluded_mlbs": [], "excluded_skus": []}
        rows = self._execute_query("SELECT exclusion_type, value FROM promo_exclusions", fetch_all=True)
        if rows:
            for row in rows:
                if row['value']: 
                    if row['exclusion_type'] == 'mlb':
                        exclusions["excluded_mlbs"].append(row['value'])
                    elif row['exclusion_type'] == 'sku':
                        exclusions["excluded_skus"].append(row['value'])
        return exclusions

    # --- SKU Processed Images Methods ---
    def add_sku_processed_image(self, sku, image_url, max_cache_per_sku_storage=20):
        """Adds a processed image URL for a SKU and trims older entries if cache size exceeded."""
        self._execute_query(
            "INSERT OR IGNORE INTO sku_processed_images (sku, image_url, added_timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (sku, image_url),
            commit=True
        )
        trim_query = """
            DELETE FROM sku_processed_images
            WHERE sku = ? AND rowid NOT IN (
                SELECT rowid FROM sku_processed_images
                WHERE sku = ? ORDER BY added_timestamp DESC LIMIT ?
            )
        """
        self._execute_query(trim_query, (sku, sku, max_cache_per_sku_storage), commit=True)

    def load_all_sku_processed_images(self):
        """Loads all SKU processed images, ordered newest first for each SKU."""
        cache_by_sku = {}
        rows = self._execute_query("SELECT sku, image_url FROM sku_processed_images ORDER BY sku, added_timestamp DESC", fetch_all=True)
        if rows:
            for row in rows:
                if row['sku'] not in cache_by_sku:
                    cache_by_sku[row['sku']] = []
                cache_by_sku[row['sku']].append(row['image_url']) 
        return cache_by_sku

    def close_db(self): 
        """Closes the database connection for the calling thread."""
        print(f"DatabaseManager: close_db() called by thread {threading.get_ident()}.")
        self._close_thread_connection()
        

    def add_to_auto_promo_queue(self, item_id, account_nickname, discount_perc, delay_minutes=0):
        """[UNIFICADO] Adiciona uma tarefa de Auto-Promoção."""
        payload = {"desired_discount_percent": discount_perc}
        return self.add_task_to_queue("AUTO_PROMO", account_nickname, item_id, payload, delay_minutes)

# DENTRO DA CLASSE DatabaseManager

    def clear_tasks_from_queue_by_type(self, task_type: str):
        """Remove todas as tarefas de um tipo específico da fila unificada."""
        if not task_type:
            return
        query = "DELETE FROM unified_task_queue WHERE task_type = ?"
        self._execute_query(query, (task_type,), commit=True)
        print(f"DB: Todas as tarefas do tipo '{task_type}' foram removidas da fila.")

    def get_task_count_by_type(self, task_type: str) -> int:
        """Conta o número total de tarefas de um tipo específico na fila."""
        if not task_type:
            return 0
        query = "SELECT COUNT(*) FROM unified_task_queue WHERE task_type = ?"
        result = self._execute_query(query, (task_type,), fetch_one=True)
        return result[0] if result else 0

    def clear_tasks_from_queue_by_type_and_status(self, task_type: str, status: str):
        """Remove todas as tarefas de um tipo e status específicos."""
        if not task_type or not status:
            return
        query = "DELETE FROM unified_task_queue WHERE task_type = ? AND status = ?"
        self._execute_query(query, (task_type, status), commit=True)
        print(f"DB: Todas as tarefas do tipo '{task_type}' com status '{status}' foram removidas.")
