"""
src/overpass_client.py

Camada de mineração de dados (data mining) geoespacial.

Responsável por:
    1. Geocodificar um bairro/cidade em uma bounding box (via Nominatim).
    2. Consultar a Overpass API (OpenStreetMap) filtrando estabelecimentos
       comerciais pelas tags correspondentes ao(s) nicho(s) solicitado(s).
    3. Normalizar o resultado bruto do OSM em uma lista de dicionários
       prontos para a etapa de análise de sites.

Usa `requests.Session` para reaproveitar conexões TCP/TLS entre chamadas,
reduzindo latência e overhead de handshake.
"""

import time
from typing import Optional

import requests

from config.settings import (
    NICHE_TAGS,
    NOMINATIM_RATE_LIMIT_SECONDS,
    NOMINATIM_URL,
    OVERPASS_URL,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)
from src.logger import get_logger

logger = get_logger(__name__)


class GeocodingError(Exception):
    """Levantada quando o bairro/cidade informado não pode ser geocodificado."""


class OverpassClient:
    """Cliente para mineração de estabelecimentos comerciais via OSM."""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._last_nominatim_call: float = 0.0

    # ------------------------------------------------------------------
    # Geocodificação
    # ------------------------------------------------------------------
    def _respect_nominatim_rate_limit(self) -> None:
        """Garante no máximo 1 requisição/segundo ao Nominatim (política de uso)."""
        elapsed = time.monotonic() - self._last_nominatim_call
        wait = NOMINATIM_RATE_LIMIT_SECONDS - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_nominatim_call = time.monotonic()

    def geocode_bairro(self, bairro: str, cidade: str, uf: str = "") -> tuple[float, float, float, float]:
        """Geocodifica um bairro + cidade em uma bounding box (S, N, W, E).

        Args:
            bairro: nome do bairro, ex. "Aquarius".
            cidade: cidade, ex. "São José dos Campos".
            uf: sigla do estado (opcional, melhora a precisão).

        Returns:
            Tupla (south, north, west, east) em graus decimais.

        Raises:
            GeocodingError: se nenhuma correspondência for encontrada.
        """
        query = f"{bairro}, {cidade}" + (f", {uf}" if uf else "") + ", Brasil"
        params = {"q": query, "format": "json", "limit": 1}

        self._respect_nominatim_rate_limit()
        try:
            response = self.session.get(
                NOMINATIM_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise GeocodingError(f"Falha ao consultar Nominatim: {exc}") from exc

        results = response.json()
        if not results:
            raise GeocodingError(
                f"Nenhuma correspondência encontrada para '{query}'. "
                "Verifique a grafia do bairro/cidade."
            )

        bbox = results[0]["boundingbox"]  # [south, north, west, east] (strings)
        south, north, west, east = (float(coord) for coord in bbox)
        logger.info(
            "Bairro '%s' geocodificado: bbox=(%.5f, %.5f, %.5f, %.5f)",
            bairro, south, north, west, east,
        )
        return south, north, west, east

    # ------------------------------------------------------------------
    # Consulta Overpass
    # ------------------------------------------------------------------
    @staticmethod
    def _build_overpass_query_for_niche(
        bbox: tuple[float, float, float, float], tags: list[tuple[str, str]]
    ) -> str:
        """Monta a query Overpass QL para um único nicho (lista de tags OSM)."""
        south, north, west, east = bbox
        bbox_str = f"{south},{west},{north},{east}"

        filters: list[str] = []
        for key, value in tags:
            filters.append(f'  node["{key}"="{value}"]({bbox_str});')
            filters.append(f'  way["{key}"="{value}"]({bbox_str});')

        body = "\n".join(filters)
        return f"[out:json][timeout:60];\n(\n{body}\n);\nout center tags;"

    def search_businesses(
        self, bairro: str, cidade: str, niches: list[str], uf: str = ""
    ) -> list[dict]:
        """Busca estabelecimentos comerciais de um bairro para os nichos dados.

        Executa uma consulta Overpass por nicho (em vez de uma única consulta
        combinada) para que cada estabelecimento retornado possa ser rotulado
        corretamente com o nicho que o originou.

        Args:
            bairro: nome do bairro.
            cidade: cidade.
            niches: lista de chaves de config.settings.NICHE_TAGS.
            uf: sigla do estado (opcional).

        Returns:
            Lista de dicts com: nome, nicho, endereco, website, lat, lon.
            Estabelecimentos que casam com mais de um nicho aparecem apenas
            uma vez (deduplicados pelo id do elemento OSM).
        """
        bbox = self.geocode_bairro(bairro, cidade, uf)

        seen_osm_ids: set[str] = set()
        leads: list[dict] = []

        for niche in niches:
            tags = NICHE_TAGS.get(niche)
            if not tags:
                logger.warning("Nicho '%s' não mapeado em NICHE_TAGS; ignorando.", niche)
                continue

            query = self._build_overpass_query_for_niche(bbox, tags)
            logger.info("Consultando Overpass API para nicho='%s' ...", niche)

            try:
                response = self.session.post(
                    OVERPASS_URL,
                    data={"data": query},
                    timeout=REQUEST_TIMEOUT_SECONDS * 3,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.error("Falha ao consultar Overpass API (nicho=%s): %s", niche, exc)
                continue

            elements = response.json().get("elements", [])
            for element in elements:
                osm_id = f'{element.get("type")}/{element.get("id")}'
                if osm_id in seen_osm_ids:
                    continue
                lead = self._normalize_element(element, bairro, niche)
                if lead is not None:
                    seen_osm_ids.add(osm_id)
                    leads.append(lead)

            # Pequena pausa cortês entre consultas para não sobrecarregar o
            # serviço público da Overpass API.
            time.sleep(0.5)

        logger.info("%d estabelecimentos encontrados em '%s'.", len(leads), bairro)
        return leads

    @staticmethod
    def _normalize_element(element: dict, bairro: str, niche: str) -> Optional[dict]:
        """Converte um elemento bruto do OSM em um registro de lead padronizado."""
        tags = element.get("tags", {})
        nome = tags.get("name")
        if not nome:
            # Estabelecimentos sem nome cadastrado não são leads acionáveis.
            return None

        website = tags.get("website") or tags.get("contact:website")
        brand = tags.get("brand") or tags.get("operator")

        endereco_partes = [
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
            tags.get("addr:suburb", bairro),
        ]
        endereco = ", ".join(p for p in endereco_partes if p)

        lat = element.get("lat") or element.get("center", {}).get("lat")
        lon = element.get("lon") or element.get("center", {}).get("lon")

        return {
            "nome": nome,
            "nicho": niche,
            "bairro": bairro,
            "endereco": endereco or None,
            "telefone": tags.get("phone") or tags.get("contact:phone"),
            "website": website,
            "marca_rede": brand,
            "latitude": lat,
            "longitude": lon,
        }
