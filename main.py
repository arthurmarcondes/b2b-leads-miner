#!/usr/bin/env python3
"""
main.py

Ponto de entrada (CLI) do B2B Leads Miner.

Orquestra o pipeline completo de prospecção B2B local:

    1. Mineração de estabelecimentos (OverpassClient)  -> quem existe no bairro
    2. Análise técnica de cada site (SiteAnalyzer)      -> como está o site
    3. Classificação comercial (LeadClassifier)         -> qual oferta cabe
    4. Exportação para CSV (DataExporter)               -> entrega para vendas

Exemplo de uso:
    python main.py --bairro "Aquarius" --cidade "São José dos Campos" --uf SP

    (por padrão usa o preset "icp": nichos com maior propensão real de
    fechar contrato, com base nos cases do portfólio da SciTec Jr.)

    python main.py --bairro "Aquarius" --cidade "São José dos Campos" \
        --nichos loja_roupas,papelaria,joalheria --excluir-redes

Para uma interface visual (sem terminal/código), use: streamlit run app.py
"""

import argparse
import sys

from config.settings import NICHE_PRESET_ICP, NICHE_TAGS, NICHE_TIER_1, NICHE_TIER_2
from src.data_exporter import DataExporter
from src.logger import get_logger
from src.pipeline import GeocodingError, run_pipeline

logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Define e parseia os argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="B2B Leads Miner — prospecção de comércios locais por bairro.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--bairro", required=True, help="Nome do bairro alvo (ex.: 'Aquarius')."
    )
    parser.add_argument(
        "--cidade", required=True, help="Cidade do bairro (ex.: 'São José dos Campos')."
    )
    parser.add_argument("--uf", default="", help="Sigla do estado (opcional, melhora a busca).")
    parser.add_argument(
        "--excluir-redes",
        action="store_true",
        help=(
            "Remove da lista estabelecimentos cadastrados com marca/rede no OSM "
            "(ex.: Carrefour, McDonald's), focando apenas em comércio independente."
        ),
    )
    parser.add_argument(
        "--nichos",
        default="icp",
        help=(
            "Nichos separados por vírgula (ex.: 'loja_roupas,papelaria'). "
            "Presets: 'icp' (recomendado — nichos com maior propensão real de "
            "fechar contrato, prioridades 1+2), 'produto' (só comércio de "
            "produto físico, prioridade 1), 'servico' (agendamento/gestão, "
            "prioridade 2), 'todos' (todos os "
            f"{len(NICHE_TAGS)} nichos disponíveis), ou 'listar' para ver as opções."
        ),
    )
    return parser.parse_args()


def resolve_niches(niches_arg: str) -> list[str]:
    """Resolve o argumento --nichos em uma lista de chaves válidas."""
    arg = niches_arg.strip().lower()

    if arg == "listar":
        print("Presets: icp (recomendado), produto, servico, todos\n")
        print("Nichos disponíveis:")
        for niche in sorted(NICHE_TAGS):
            print(f"  - {niche}")
        sys.exit(0)

    if arg == "icp":
        return NICHE_PRESET_ICP
    if arg == "produto":
        return NICHE_TIER_1
    if arg == "servico":
        return NICHE_TIER_2
    if arg == "todos":
        return list(NICHE_TAGS.keys())

    requested = [n.strip() for n in niches_arg.split(",") if n.strip()]
    invalid = [n for n in requested if n not in NICHE_TAGS]
    if invalid:
        logger.error(
            "Nicho(s) inválido(s): %s. Use --nichos listar para ver as opções.",
            ", ".join(invalid),
        )
        sys.exit(1)
    return requested


def main() -> None:
    args = parse_args()
    niches = resolve_niches(args.nichos)
    logger.info(
        "Iniciando prospecção: bairro='%s', cidade='%s', nichos=%s",
        args.bairro, args.cidade, niches,
    )

    try:
        leads = run_pipeline(args.bairro, args.cidade, args.uf, niches, args.excluir_redes)
    except GeocodingError as exc:
        logger.error("Erro de geocodificação: %s", exc)
        sys.exit(1)

    DataExporter().export(leads, args.bairro)


if __name__ == "__main__":
    main()
