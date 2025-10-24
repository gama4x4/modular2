# services/task_enqueue.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional


@dataclass
class EnqueueItem:
    """
    Representa um item a ser enfileirado.
    Preencha ao menos account_nickname e item_id OU forneça um payload com contexto.
    """
    account_nickname: str
    item_id: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None
    delay_minutes: int = 0


class TaskEnqueueService:
    """
    Serviço genérico para enfileirar tarefas na unified_task_queue.
    Usa db_manager.add_task_to_queue(task_type, account_nickname, item_id, payload, delay_minutes)
    que você já tem implementado.
    """

    def __init__(self, db_manager):
        self.db = db_manager

    # -------------------------
    # GENÉRICO
    # -------------------------
    def enqueue(self, task_type: str, items: List[EnqueueItem]) -> int:
        """
        Enfileira uma lista de itens para um task_type específico.
        Retorna quantos foram adicionados com sucesso.
        """
        if not items:
            return 0

        ok = 0
        for it in items:
            payload = it.payload or {}
            # garanta que payload é básico-serializável (o add_task_to_queue faz json.dumps)
            success = self.db.add_task_to_queue(
                task_type=task_type,
                account_nickname=it.account_nickname,
                item_id=it.item_id,
                payload=payload,
                delay_minutes=it.delay_minutes,
            )
            if success:
                ok += 1
        return ok

    # -------------------------
    # ATALHOS COMUNS (opcionais)
    # -------------------------
    def enqueue_auto_promo(self, items: List[EnqueueItem]) -> int:
        """Atalho para AUTO_PROMO."""
        return self.enqueue("AUTO_PROMO", items)

    def enqueue_price_check(self, items: List[EnqueueItem]) -> int:
        """Atalho para PRICE_CHECK."""
        return self.enqueue("PRICE_CHECK", items)

    def enqueue_stock_divergence(self, items: List[EnqueueItem]) -> int:
        """Atalho para STOCK_DIVERGENCE."""
        return self.enqueue("STOCK_DIVERGENCE", items)

    # -------------------------
    # (Opcional) Placeholders de mapeamento SKU→item_id
    # -------------------------
    def sku_to_ml_item_id(self, sku: str) -> Optional[str]:
        """
        Placeholder: se você quiser enfileirar por SKU, implemente o mapeamento aqui.
        Ex.: consultar tabela local de anúncios ou uma cache que relacione SKU↔MLB.
        """
        # TODO: implemente sua lógica real
        return None

    def enqueue_by_skus(self, task_type: str, account_nickname: str, skus: List[str], extra_payload: Dict[str, Any] | None = None) -> int:
        """
        Exemplo de conveniência: recebe SKUs e tenta mapear para item_id.
        Só enfileira os que conseguir resolver.
        """
        items: List[EnqueueItem] = []
        for sku in skus:
            ml_item_id = self.sku_to_ml_item_id(sku)
            if not ml_item_id:
                continue
            items.append(EnqueueItem(
                account_nickname=account_nickname,
                item_id=ml_item_id,
                payload=(extra_payload or {})
            ))
        return self.enqueue(task_type, items)
