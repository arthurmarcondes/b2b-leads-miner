"""
tests/test_lead_classifier.py

Testes unitários da regra de negócio mais crítica do projeto: a
classificação de leads. Como essas regras definem qual oferta comercial
cada estabelecimento recebe, elas precisam de cobertura explícita e
independente de chamadas de rede (usamos SiteAnalysisResult "sintéticos").

Executar com:
    python -m unittest discover -s tests -v
"""

import unittest

from config.settings import CATEGORY_DATA_BI, CATEGORY_NO_SITE, CATEGORY_OPTIMIZATION
from src.lead_classifier import LeadClassifier
from src.site_analyzer import SiteAnalysisResult


class TestLeadClassifier(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = LeadClassifier()

    def test_sem_site_deve_classificar_criar_site_do_zero(self) -> None:
        analysis = SiteAnalysisResult(has_site=False)
        result = self.classifier.classify(analysis)
        self.assertEqual(result.categoria, CATEGORY_NO_SITE)

    def test_site_rapido_e_seguro_deve_classificar_bi(self) -> None:
        analysis = SiteAnalysisResult(
            has_site=True,
            is_https=True,
            ssl_valid=True,
            status_code=200,
            response_time_seconds=0.8,
        )
        result = self.classifier.classify(analysis)
        self.assertEqual(result.categoria, CATEGORY_DATA_BI)

    def test_site_sem_https_deve_classificar_otimizacao(self) -> None:
        analysis = SiteAnalysisResult(
            has_site=True,
            is_https=False,
            ssl_valid=False,
            status_code=200,
            response_time_seconds=0.5,
        )
        result = self.classifier.classify(analysis)
        self.assertEqual(result.categoria, CATEGORY_OPTIMIZATION)

    def test_site_lento_deve_classificar_otimizacao(self) -> None:
        analysis = SiteAnalysisResult(
            has_site=True,
            is_https=True,
            ssl_valid=True,
            status_code=200,
            response_time_seconds=5.0,
        )
        result = self.classifier.classify(analysis)
        self.assertEqual(result.categoria, CATEGORY_OPTIMIZATION)

    def test_site_com_erro_http_deve_classificar_otimizacao(self) -> None:
        analysis = SiteAnalysisResult(
            has_site=True,
            is_https=True,
            ssl_valid=True,
            status_code=500,
            response_time_seconds=0.3,
        )
        result = self.classifier.classify(analysis)
        self.assertEqual(result.categoria, CATEGORY_OPTIMIZATION)


if __name__ == "__main__":
    unittest.main()
