"""
src/data_exporter.py

Camada de persistência/exportação. Consolida os leads processados em um
DataFrame do pandas, salva em CSV e imprime um resumo estatístico por
categoria — útil tanto para consumo humano (planilha) quanto para
pipelines posteriores (dashboards, CRM, etc.).
"""

from datetime import datetime
from pathlib import Path

import pandas as pd

from config.settings import OUTPUT_DIR
from src.logger import get_logger

logger = get_logger(__name__)

COLUMN_ORDER = [
    "nome",
    "nicho",
    "categoria",
    "bairro",
    "endereco",
    "telefone",
    "website",
    "url_final",
    "status_code",
    "is_https",
    "ssl_valid",
    "response_time_seconds",
    "motivos",
    "latitude",
    "longitude",
]


class DataExporter:
    """Responsável por consolidar e persistir os resultados finais em CSV."""

    def __init__(self, output_dir: Path = OUTPUT_DIR) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(self, leads: list[dict], bairro: str) -> Path:
        """Salva a lista de leads processados em um arquivo CSV.

        Args:
            leads: lista de dicionários já com colunas de análise/classificação.
            bairro: usado para compor o nome do arquivo de saída.

        Returns:
            Path do arquivo CSV gerado.
        """
        if not leads:
            logger.warning("Nenhum lead para exportar.")
            df = pd.DataFrame(columns=COLUMN_ORDER)
        else:
            df = pd.DataFrame(leads)
            existing_cols = [c for c in COLUMN_ORDER if c in df.columns]
            remaining_cols = [c for c in df.columns if c not in existing_cols]
            df = df[existing_cols + remaining_cols]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        slug = bairro.strip().lower().replace(" ", "_")
        filename = f"leads_{slug}_{timestamp}.csv"
        filepath = self.output_dir / filename

        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        logger.info("Arquivo exportado: %s (%d leads)", filepath, len(df))

        self._print_summary(df)
        return filepath

    @staticmethod
    def _print_summary(df: pd.DataFrame) -> None:
        """Imprime no console um resumo de contagem por categoria."""
        if df.empty or "categoria" not in df.columns:
            print("\nNenhum resultado para resumir.")
            return

        print("\n" + "=" * 50)
        print("RESUMO DA PROSPECÇÃO")
        print("=" * 50)
        counts = df["categoria"].value_counts()
        total = len(df)
        for categoria, qtd in counts.items():
            pct = (qtd / total) * 100
            print(f"  {categoria:<30} {qtd:>4} leads  ({pct:5.1f}%)")
        print("-" * 50)
        print(f"  {'TOTAL':<30} {total:>4} leads")
        print("=" * 50 + "\n")
