"""
src/pipeline.py

Orquestração do pipeline de prospecção, extraída para um módulo compartilhado
para que tanto o CLI (main.py) quanto a interface web (app.py) usem exatamente
a mesma lógica de negócio, evitando duplicação e divergência de comportamento.
"""

from dataclasses import asdict
from typing import Callable, Optional

from src.data_exporter import COLUMN_ORDER
from src.lead_classifier import LeadClassifier
from src.logger import get_logger
from src.overpass_client import GeocodingError, OverpassClient
from src.site_analyzer import SiteAnalyzer

logger = get_logger(__name__)

ProgressCallback = Callable[[int, int, str], None]


def run_pipeline(
    bairro: str,
    cidade: str,
    uf: str,
    niches: list[str],
    excluir_redes: bool = False,
    on_progress: Optional[ProgressCallback] = None,
) -> list[dict]:
    """Executa mineração -> análise técnica -> classificação para um bairro.

    Args:
        bairro: nome do bairro alvo.
        cidade: cidade correspondente.
        uf: sigla do estado (opcional).
        niches: lista de chaves de nicho (config.settings.NICHE_TAGS).
        excluir_redes: se True, remove estabelecimentos com tag de marca/rede.
        on_progress: callback opcional chamado a cada lead processado, como
            on_progress(indice_atual, total, nome_do_lead) — usado pela UI
            (Streamlit) para atualizar uma barra de progresso em tempo real.

    Returns:
        Lista de dicts com os leads já processados e classificados, prontos
        para exportação (CSV) ou exibição em tabela.

    Raises:
        GeocodingError: se o bairro/cidade não puder ser geocodificado.
    """
    overpass_client = OverpassClient()
    site_analyzer = SiteAnalyzer()
    classifier = LeadClassifier()

    raw_leads = overpass_client.search_businesses(bairro, cidade, niches, uf)

    if excluir_redes:
        antes = len(raw_leads)
        raw_leads = [lead for lead in raw_leads if not lead.get("marca_rede")]
        removidos = antes - len(raw_leads)
        if removidos:
            logger.info(
                "%d estabelecimento(s) de rede/franquia removido(s) (excluir_redes).",
                removidos,
            )

    if not raw_leads:
        logger.warning("Nenhum estabelecimento encontrado para os critérios informados.")
        return []

    processed_leads: list[dict] = []
    total = len(raw_leads)

    for idx, lead in enumerate(raw_leads, start=1):
        logger.info("[%d/%d] Analisando: %s", idx, total, lead["nome"])
        if on_progress is not None:
            on_progress(idx, total, lead["nome"])

        try:
            analysis = site_analyzer.analyze(lead.get("website"))
            classification = classifier.classify(analysis)
        except Exception as exc:  # noqa: BLE001 - pipeline não deve parar por 1 lead
            logger.error("Falha ao processar '%s': %s", lead["nome"], exc)
            analysis = None
            classification = None

        record = {**lead}
        if analysis is not None:
            analysis_dict = asdict(analysis)
            record.update(
                {
                    "url_final": analysis_dict.get("url_final"),
                    "status_code": analysis_dict.get("status_code"),
                    "is_https": analysis_dict.get("is_https"),
                    "ssl_valid": analysis_dict.get("ssl_valid"),
                    "response_time_seconds": analysis_dict.get("response_time_seconds"),
                }
            )
        if classification is not None:
            record["categoria"] = classification.categoria
            record["motivos"] = " | ".join(classification.motivos)
        else:
            record["categoria"] = "Erro no processamento"
            record["motivos"] = "Falha inesperada durante análise/classificação."

        processed_leads.append(record)

    return processed_leads


__all__ = ["run_pipeline", "GeocodingError", "COLUMN_ORDER"]
