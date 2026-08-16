"""
src/logger.py

Configuração centralizada de logging. Todos os módulos do projeto devem
obter seu logger através de `get_logger(__name__)` em vez de instanciar
`logging` diretamente, garantindo formatação e destino (arquivo + console)
consistentes em todo o pipeline.
"""

import logging
import sys
from pathlib import Path

from config.settings import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Retorna um logger configurado com saída para console e arquivo.

    Args:
        name: normalmente `__name__` do módulo chamador.
        level: nível mínimo de log (default: INFO).

    Returns:
        Instância de logging.Logger pronta para uso.
    """
    logger = logging.getLogger(name)

    # Evita duplicar handlers se get_logger for chamado múltiplas vezes
    # para o mesmo módulo (ex.: em notebooks ou re-imports).
    if logger.handlers:
        return logger

    logger.setLevel(level)

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            Path(LOG_DIR) / "b2b_leads_miner.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Se o sistema de arquivos não permitir escrita (ex.: ambiente
        # restrito), seguimos apenas com log em console em vez de falhar.
        logger.warning("Não foi possível criar arquivo de log; usando apenas console.")

    logger.propagate = False
    return logger
