# services/abc_importer.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

# pandas é usado apenas aqui; se não estiver instalado, tratamos o erro.
try:
    import pandas as pd
except Exception as e:
    pd = None


@dataclass
class ABCImportResult:
    success: bool
    message: str
    df: Optional["pd.DataFrame"] = None
    warnings: Optional[List[str]] = None


class ABCImporter:
    """
    Serviço de importação da Curva ABC a partir de um arquivo .xlsx.
    - Não grava no banco aqui (mantemos modular). Apenas lê e valida.
    - Próximo passo: persistência (services/abc_service.py) ou método no DatabaseManager.
    """

    REQUIRED_ANY_OF = [
        ["SKU", "Codigo", "Código", "codigo", "código"],  # coluna de identificador
        ["Valor", "valor", "Receita", "receita"],         # métrica de valor
        ["Quantidade", "Qtd", "qtd", "quantidade"],       # métrica de quantidade
    ]

    def __init__(self, sort_by: str = "Valor"):
        """
        sort_by: "Valor" ou "Quantidade" (mantém compatibilidade com o diálogo).
        """
        self.sort_by = sort_by

    def import_file(self, file_path: str) -> ABCImportResult:
        if not os.path.isfile(file_path):
            return ABCImportResult(False, f"Arquivo não encontrado: {file_path}")

        if pd is None:
            return ABCImportResult(
                False,
                "Pandas não está instalado. Instale com: pip install pandas openpyxl",
            )

        try:
            df = pd.read_excel(file_path, engine="openpyxl")
        except Exception as e:
            return ABCImportResult(False, f"Falha ao ler Excel: {e}")

        # Normaliza nomes de colunas (strip + casefold)
        original_cols = list(df.columns)
        norm_map = {c: c.strip() for c in original_cols}
        df.rename(columns=norm_map, inplace=True)

        # Mapeamento flexível de colunas (aceita variações)
        resolved_cols: Dict[str, Optional[str]] = {
            "sku": self._resolve_col(df.columns, self.REQUIRED_ANY_OF[0]),
            "valor": self._resolve_col(df.columns, self.REQUIRED_ANY_OF[1]),
            "quantidade": self._resolve_col(df.columns, self.REQUIRED_ANY_OF[2]),
        }

        warnings: List[str] = []
        if resolved_cols["sku"] is None:
            return ABCImportResult(False, "Coluna de SKU/Código não encontrada no arquivo.")
        if resolved_cols["valor"] is None and resolved_cols["quantidade"] is None:
            return ABCImportResult(
                False,
                "Nenhuma métrica encontrada. Informe uma coluna de 'Valor' ou 'Quantidade'.",
            )
        if resolved_cols["valor"] is None:
            warnings.append("Coluna de Valor não encontrada — será ignorada.")
        if resolved_cols["quantidade"] is None:
            warnings.append("Coluna de Quantidade não encontrada — será ignorada.")

        # Cria um DF enxuto com colunas padronizadas
        cols_to_take = [c for c in [resolved_cols["sku"], resolved_cols["valor"], resolved_cols["quantidade"]] if c]
        df_out = df[cols_to_take].copy()

        # Renomeia para padrão interno
        rename_map = {}
        if resolved_cols["sku"]:
            rename_map[resolved_cols["sku"]] = "SKU"
        if resolved_cols["valor"]:
            rename_map[resolved_cols["valor"]] = "Valor"
        if resolved_cols["quantidade"]:
            rename_map[resolved_cols["quantidade"]] = "Quantidade"
        df_out.rename(columns=rename_map, inplace=True)

        # Ordenação conforme escolha
        sort_key = "Valor" if (self.sort_by or "").lower().startswith("valor") and "Valor" in df_out.columns else \
                   "Quantidade" if "Quantidade" in df_out.columns else None
        if sort_key:
            try:
                df_out[sort_key] = pd.to_numeric(df_out[sort_key], errors="coerce")
            except Exception:
                warnings.append(f"Não foi possível converter '{sort_key}' para número; ordenação pode ficar imprecisa.")
            df_out.sort_values(by=sort_key, ascending=False, inplace=True, na_position="last")

        # Calcula classe ABC (simples, com base na cumulativa da coluna escolhida)
        if sort_key:
            total = df_out[sort_key].fillna(0).sum()
            if total > 0:
                cumul = df_out[sort_key].fillna(0).cumsum() / total
                df_out["Classe_ABC"] = cumul.apply(self._abc_bucket)
            else:
                warnings.append("Total da métrica escolhida é 0 — não foi possível classificar ABC.")
                df_out["Classe_ABC"] = "C"
        else:
            df_out["Classe_ABC"] = "C"

        return ABCImportResult(True, "Curva ABC importada com sucesso.", df=df_out.reset_index(drop=True), warnings=warnings)

    # ------------------------
    # Placeholders de persistência
    # ------------------------
    def save_to_db(self, db_manager, df: "pd.DataFrame") -> None:
        """
        Placeholder: salve o resultado no banco (ex.: tabela tiny_abc_curve).
        Implemente depois conforme seu schema/uso.
        """
        # Exemplo:
        # db_manager.replace_table("tiny_abc_curve", df)
        print("[ABCImporter] save_to_db() ainda não implementado.")

    def map_to_tiny_products(self, db_manager, df: "pd.DataFrame") -> None:
        """
        Placeholder: faça o join SKU→tiny_products e grave classe ABC no catálogo.
        """
        print("[ABCImporter] map_to_tiny_products() ainda não implementado.")

    # ------------------------
    # Helpers internos
    # ------------------------
    @staticmethod
    def _resolve_col(cols: List[str], candidates: List[str]) -> Optional[str]:
        lowered = {c.lower(): c for c in cols}
        for cand in candidates:
            key = cand.lower()
            if key in lowered:
                return lowered[key]
        return None

    @staticmethod
    def _abc_bucket(r: float) -> str:
        # Regra simples (você pode ajustar): A=70%, B=20%, C=10%
        if r <= 0.70:
            return "A"
        if r <= 0.90:
            return "B"
        return "C"
