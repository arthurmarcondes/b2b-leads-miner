"""
src/site_analyzer.py

Camada de análise técnica de sites. Para cada lead com website, realiza uma
requisição HTTP real e coleta sinais objetivos de saúde técnica:

    - Disponibilidade (o site respondeu?)
    - Código de status HTTP
    - Presença/validade de HTTPS
    - Tempo de resposta (latência)

Esses sinais alimentam a etapa de classificação (src/lead_classifier.py).
"""

import time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
import urllib3

from config.settings import REQUEST_TIMEOUT_SECONDS
from src.logger import get_logger

logger = get_logger(__name__)

# Sites com certificados inválidos ainda precisam ser detectados (é
# justamente um dos motivos de classificação em "Otimização/Segurança"),
# então desabilitamos o warning de verify=False para a chamada de fallback,
# mas ainda registramos o problema explicitamente no resultado.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class SiteAnalysisResult:
    """Resultado estruturado da análise técnica de um site."""

    has_site: bool
    url_original: Optional[str] = None
    url_final: Optional[str] = None
    is_https: bool = False
    ssl_valid: bool = False
    status_code: Optional[int] = None
    response_time_seconds: Optional[float] = None
    error: Optional[str] = None

    @property
    def is_http_error(self) -> bool:
        return self.status_code is None or self.status_code >= 400

    @property
    def is_slow(self) -> bool:
        from config.settings import SLOW_SITE_THRESHOLD_SECONDS

        return (
            self.response_time_seconds is not None
            and self.response_time_seconds > SLOW_SITE_THRESHOLD_SECONDS
        )


class SiteAnalyzer:
    """Executa checagens de saúde técnica (HTTP/HTTPS/latência) sobre um site."""

    def __init__(self, timeout: int = REQUEST_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; B2BLeadsMinerBot/1.0; "
                    "+https://github.com/seu-usuario/b2b-leads-miner)"
                )
            }
        )

    def analyze(self, website: Optional[str]) -> SiteAnalysisResult:
        """Analisa um website e retorna um SiteAnalysisResult.

        Args:
            website: URL do site (pode vir sem esquema, ex. "www.site.com.br").

        Returns:
            SiteAnalysisResult preenchido. Se `website` for None/vazio,
            retorna has_site=False imediatamente (sem requisição de rede).
        """
        if not website or not website.strip():
            return SiteAnalysisResult(has_site=False)

        url = self._normalize_url(website)

        try:
            start = time.perf_counter()
            response = self.session.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=True,
            )
            elapsed = time.perf_counter() - start

            final_scheme = urlparse(response.url).scheme
            return SiteAnalysisResult(
                has_site=True,
                url_original=url,
                url_final=response.url,
                is_https=final_scheme == "https",
                ssl_valid=final_scheme == "https",
                status_code=response.status_code,
                response_time_seconds=round(elapsed, 3),
            )

        except requests.exceptions.SSLError as exc:
            # Site existe, mas o certificado SSL é inválido/expirado/self-signed.
            # Isso é, por si só, um forte indicativo de "Otimização/Segurança".
            logger.warning("SSL inválido em %s: %s", url, exc)
            return self._retry_ignoring_ssl(url, ssl_error=str(exc))

        except requests.exceptions.Timeout:
            logger.warning("Timeout ao acessar %s", url)
            return SiteAnalysisResult(
                has_site=True, url_original=url, error="timeout"
            )

        except requests.exceptions.ConnectionError as exc:
            logger.warning("Erro de conexão em %s: %s", url, exc)
            return SiteAnalysisResult(
                has_site=True, url_original=url, error="connection_error"
            )

        except requests.RequestException as exc:
            logger.warning("Erro inesperado ao acessar %s: %s", url, exc)
            return SiteAnalysisResult(
                has_site=True, url_original=url, error=str(exc)
            )

    def _retry_ignoring_ssl(self, url: str, ssl_error: str) -> SiteAnalysisResult:
        """Refaz a requisição sem validar o certificado, apenas para confirmar
        que o site está *no ar* mesmo com SSL quebrado (útil para diferenciar
        "site fora do ar" de "site no ar com SSL inválido").
        """
        try:
            start = time.perf_counter()
            response = self.session.get(
                url, timeout=self.timeout, allow_redirects=True, verify=False
            )
            elapsed = time.perf_counter() - start
            return SiteAnalysisResult(
                has_site=True,
                url_original=url,
                url_final=response.url,
                is_https=urlparse(response.url).scheme == "https",
                ssl_valid=False,  # certificado confirmadamente inválido
                status_code=response.status_code,
                response_time_seconds=round(elapsed, 3),
                error=f"ssl_invalid: {ssl_error[:120]}",
            )
        except requests.RequestException as exc:
            return SiteAnalysisResult(
                has_site=True,
                url_original=url,
                ssl_valid=False,
                error=f"ssl_invalid_and_unreachable: {exc}",
            )

    @staticmethod
    def _normalize_url(website: str) -> str:
        """Garante que a URL tenha um esquema (http/https) antes da requisição."""
        website = website.strip()
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        return website
