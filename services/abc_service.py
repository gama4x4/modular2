# services/abc_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

try:
    import pandas as pd
except Exception:
    pd = None


@dataclass
class ABCApplyReport:
    success: bool
    message: str
    updated: int = 0
    not_found: List[str] = None
    warnings: List[str] = None


class ABCService:
    """
    Aplica a Curva ABC no banco (tiny_products):
      - Atualiza vendas_qtd, vendas_valor
      - Atualiza curva_a_posicao (A/B/C) e curva_a_rank
      - Atualiza import_sequence (ordem da planilha)
    """

    def __init__(self, normalize_sku: bool = True):
        self.normalize_sku = normalize_sku

    def apply_to_db(self, db_manager, df: "pd.DataFrame") -> ABCApplyReport:
        if pd is None:
            return ABCApplyReport(False, "Pandas não está instalado.")

        required = ["SKU"]
        missing = [c for c in required if c not in df.columns]
        if missing:
            return ABCApplyReport(False, f"Colunas obrigatórias ausentes: {', '.join(missing)}")

        # Normalizações de colunas opcionais
        has_valor = "Valor" in df.columns
        has_qtd = "Quantidade" in df.columns
        has_class = "Classe_ABC" in df.columns

        work = df.copy()

        # Normaliza SKU
        if self.normalize_sku:
            work["SKU"] = work["SKU"].astype(str).str.strip().str.upper()
        else:
            work["SKU"] = work["SKU"].astype(str)

        # Converte métricas numéricas
        if has_valor:
            work["Valor"] = pd.to_numeric(work["Valor"], errors="coerce").fillna(0.0)
        else:
            work["Valor"] = 0.0

        if has_qtd:
            work["Quantidade"] = pd.to_numeric(work["Quantidade"], errors="coerce").fillna(0.0)
        else:
            work["Quantidade"] = 0.0

        # Define rank baseado na métrica disponível (prioriza "Valor")
        sort_key = "Valor" if has_valor else ("Quantidade" if has_qtd else None)
        if sort_key:
            work = work.sort_values(by=sort_key, ascending=False, na_position="last")
        work = work.reset_index(drop=True)

        # Classe ABC default = 'C' se não vier na planilha
        if not has_class:
            work["Classe_ABC"] = "C"

        # Sequência de import (1..n)
        work["import_sequence"] = work.index + 1

        # Aplica no DB
        updated_count = 0
        not_found: List[str] = []
        warnings: List[str] = []

        # Limpa classificações antigas (mantendo schema existente)
        try:
            # zera curva/rank/seq e também dados de vendas
            db_manager.clear_all_abc_positions()
        except Exception as e:
            warnings.append(f"Falha ao limpar posições ABC existentes: {e}")

        # Atualização linha a linha — simples e explícita
        for _, row in work.iterrows():
            sku = row["SKU"]
            qtd = float(row.get("Quantidade", 0) or 0)
            val = float(row.get("Valor", 0) or 0)
            cls = str(row.get("Classe_ABC") or "C").strip().upper()[:1]
            rank = int(row.get("import_sequence", 0))  # usamos import_sequence como rank

            # 1) Atualiza vendas
            try:
                db_manager.update_product_abc_sales_data(sku=sku, qtd=qtd, valor=val)
            except Exception as e:
                warnings.append(f"SKU {sku}: erro ao atualizar vendas ({e}).")
                continue

            # 2) Atualiza classificação e rank
            try:
                # Atualiza curva/rank/seq diretamente
                db_manager._execute_query(
                    """
                    UPDATE tiny_products 
                       SET curva_a_posicao = ?, 
                           curva_a_rank = ?, 
                           import_sequence = ?, 
                           atualizado_em = CURRENT_TIMESTAMP
                     WHERE UPPER(TRIM(sku)) = ?
                    """,
                    (cls, rank, rank, sku),
                    commit=True
                )
                # Verifica se houve match
                rowcount = db_manager._execute_query("SELECT changes()", fetch_one=True)[0]
                if rowcount and rowcount > 0:
                    updated_count += 1
                else:
                    not_found.append(sku)
            except Exception as e:
                warnings.append(f"SKU {sku}: erro ao atualizar ABC ({e}).")

        msg = f"Aplicação da Curva ABC concluída. Atualizados: {updated_count}."
        if not_found:
            msg += f" Não encontrados: {len(not_found)}."

        return ABCApplyReport(True, msg, updated=updated_count, not_found=not_found, warnings=warnings)
