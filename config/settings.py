"""
config/settings.py

Configurações centrais do projeto: nichos de mercado mapeados para tags do
OpenStreetMap, thresholds de performance/segurança e constantes gerais.

Manter todas as "constantes de negócio" neste módulo facilita a manutenção:
adicionar um novo nicho ou recalibrar um limite de lentidão não exige tocar
na lógica de scraping/classificação.
"""

from pathlib import Path

# --------------------------------------------------------------------------
# Diretórios
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

# --------------------------------------------------------------------------
# APIs externas (sem necessidade de chave paga)
# --------------------------------------------------------------------------
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# A política de uso do Nominatim exige um User-Agent identificável e
# no máximo 1 requisição por segundo. Ver: https://operations.osmfoundation.org/policies/nominatim/
USER_AGENT = "b2b-leads-miner/1.0 (contato: seu-email@dominio.com)"
NOMINATIM_RATE_LIMIT_SECONDS = 1.1

# --------------------------------------------------------------------------
# Nichos de mercado -> tags OpenStreetMap (chave, valor)
# Cada nicho pode ter mais de uma combinação de tags equivalentes.
# Referência de tags: https://wiki.openstreetmap.org/wiki/Map_features
#
# Curadoria alinhada ao ICP (Ideal Customer Profile) da SciTec Jr., com base
# nos cases reais do portfólio (Miah Moda, Ustyle, Sansomed): o padrão de
# sucesso é comércio com CATÁLOGO DE PRODUTO FÍSICO (candidato natural a
# e-commerce) e serviços que dependem de agendamento/gestão de clientes.
# Restaurante foi removido: já resolve presença digital via iFood/Rappi,
# reduzindo a propensão de fechar um site próprio.
# --------------------------------------------------------------------------
NICHE_TAGS: dict[str, list[tuple[str, str]]] = {
    # --- Prioridade 1: comércio de produto físico (maior fit com o ICP) ---
    "loja_roupas": [("shop", "clothes")],
    "loja_calcados": [("shop", "shoes")],
    "loja_presentes": [("shop", "gift"), ("shop", "variety_store")],
    "papelaria": [("shop", "stationery"), ("shop", "books")],
    "armarinho": [("shop", "haberdashery"), ("shop", "fabric")],
    "loja_moveis": [("shop", "furniture")],
    "joalheria": [("shop", "jewelry")],
    "loja_bebes": [("shop", "baby_goods")],
    "loja_brinquedos": [("shop", "toys")],
    "otica": [("shop", "optician")],
    "petshop": [("shop", "pet")],
    "loja_eletronicos": [("shop", "electronics"), ("shop", "computer")],

    # --- Prioridade 2: serviço com agendamento/gestão de clientes ---
    "salao_beleza": [("shop", "hairdresser"), ("shop", "beauty")],
    "academia": [("leisure", "fitness_centre")],
    "imobiliaria": [("office", "estate_agent")],
    "farmacia": [("amenity", "pharmacy")],

    # --- Prioridade 3: serviço profissional (presença/portfólio) ---
    "advocacia": [("office", "lawyer")],
    "contabilidade": [("office", "accountant")],
    "clinica_odontologica": [("amenity", "dentist")],
    "clinica_medica": [("amenity", "clinic"), ("healthcare", "clinic")],
    "oficina_mecanica": [("shop", "car_repair")],
    "lanchonete": [("amenity", "fast_food"), ("amenity", "cafe")],
}

# Presets de nichos por prioridade de ICP, usados pelo argumento --nichos.
# "icp" = prioridades 1 + 2 (maior propensão real de fechar contrato).
NICHE_TIER_1 = [
    "loja_roupas", "loja_calcados", "loja_presentes", "papelaria",
    "armarinho", "loja_moveis", "joalheria", "loja_bebes",
    "loja_brinquedos", "otica", "petshop", "loja_eletronicos",
]
NICHE_TIER_2 = ["salao_beleza", "academia", "imobiliaria", "farmacia"]
NICHE_TIER_3 = [
    "advocacia", "contabilidade", "clinica_odontologica",
    "clinica_medica", "oficina_mecanica", "lanchonete",
]
NICHE_PRESET_ICP = NICHE_TIER_1 + NICHE_TIER_2

# --------------------------------------------------------------------------
# Thresholds de análise técnica de sites
# --------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 10
SLOW_SITE_THRESHOLD_SECONDS = 2.5  # acima disso, o site é considerado lento
HTTP_ERROR_STATUS_FLOOR = 400  # status >= 400 é considerado erro

# --------------------------------------------------------------------------
# Categorias de classificação de leads
# --------------------------------------------------------------------------
CATEGORY_NO_SITE = "Criar Site do Zero"
CATEGORY_OPTIMIZATION = "Otimização / Segurança"
CATEGORY_DATA_BI = "Análise de Dados / BI"
