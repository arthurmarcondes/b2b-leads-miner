"""
src/lead_classifier.py

Camada de regras de negócio: converte o resultado técnico de
SiteAnalyzer (src/site_analyzer.py) em uma categoria comercial acionável
para a equipe de vendas/prospecção.

As três categorias e suas regras (nessa ordem de precedência):

1. "Criar Site do Zero"
   -> A empresa não possui website (ou o campo não foi cadastrado no OSM).

2. "Otimização / Segurança"
   -> A empresa possui site, mas ele apresenta pelo menos um problema:
      erro HTTP (>=400), ausência/erro de HTTPS, ou tempo de resposta
      acima do threshold de lentidão.

3. "Análise de Dados / BI"
   -> A empresa possui site saudável (HTTPS válido, status 2xx/3xx e
      resposta rápida) — ou seja, já tem presença digital madura e é
      candidata a ofertas de analytics, dashboards e integrações de dados.
"""

from dataclasses import dataclass

from config.settings import CATEGORY_DATA_BI, CATEGORY_NO_SITE, CATEGORY_OPTIMIZATION
from src.site_analyzer import SiteAnalysisResult


@dataclass
class ClassificationResult:
    """Categoria final + motivo(s) legíveis para justificar a classificação."""

    categoria: str
    motivos: list[str]


class LeadClassifier:
    """Aplica as regras de negócio de classificação de leads."""

    @staticmethod
    def classify(analysis: SiteAnalysisResult) -> ClassificationResult:
        """Classifica um lead com base no resultado da análise técnica do site.

        Args:
            analysis: SiteAnalysisResult produzido por SiteAnalyzer.analyze().

        Returns:
            ClassificationResult com a categoria e a justificativa.
        """
        if not analysis.has_site:
            return ClassificationResult(
                categoria=CATEGORY_NO_SITE,
                motivos=["Nenhum website cadastrado/encontrado para o estabelecimento."],
            )

        motivos: list[str] = []

        if analysis.error and "unreachable" in analysis.error:
            motivos.append("Site fora do ar / inacessível.")
        if analysis.is_http_error:
            status = analysis.status_code if analysis.status_code else "sem resposta"
            motivos.append(f"Erro HTTP (status={status}).")
        if not analysis.is_https or not analysis.ssl_valid:
            motivos.append("Sem HTTPS válido (certificado SSL ausente ou inválido).")
        if analysis.is_slow:
            motivos.append(
                f"Tempo de resposta lento ({analysis.response_time_seconds}s)."
            )
        if analysis.error and "timeout" in analysis.error:
            motivos.append("Timeout ao carregar a página.")

        if motivos:
            return ClassificationResult(
                categoria=CATEGORY_OPTIMIZATION, motivos=motivos
            )

        return ClassificationResult(
            categoria=CATEGORY_DATA_BI,
            motivos=["Site rápido, seguro (HTTPS) e sem erros — pronto para BI/analytics."],
        )
