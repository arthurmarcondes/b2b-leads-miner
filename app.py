"""
app.py

Interface web do B2B Leads Miner, construída com Streamlit.

Permite que qualquer pessoa da equipe (comercial, vendas) rode uma
prospecção preenchendo um formulário no navegador — sem abrir terminal,
editar código ou instalar nada além do navegador (quando hospedado).

Como rodar localmente:
    streamlit run app.py

Como disponibilizar para o time sem precisar instalar nada (recomendado):
    1. Suba este repositório no GitHub.
    2. Acesse https://share.streamlit.io, conecte sua conta GitHub.
    3. Aponte para este repositório e o arquivo "app.py".
    4. Você recebe uma URL pública (ex.: seu-app.streamlit.app) — qualquer
       pessoa do time pode acessar direto pelo navegador, sem instalar nada.
"""

import pandas as pd
import streamlit as st

from config.settings import (
    CATEGORY_DATA_BI,
    CATEGORY_NO_SITE,
    CATEGORY_OPTIMIZATION,
    NICHE_PRESET_ICP,
    NICHE_TAGS,
    NICHE_TIER_1,
    NICHE_TIER_2,
    NICHE_TIER_3,
)
from src.data_exporter import COLUMN_ORDER
from src.pipeline import GeocodingError, run_pipeline

st.set_page_config(
    page_title="Marcondes|Leads Finder",
    layout="wide",
)

PRESETS = {
    "Recomendado (ICP)": NICHE_PRESET_ICP,
    "Só comércio de produto": NICHE_TIER_1,
    "Só serviço c/ agendamento": NICHE_TIER_2,
    "Serviço profissional": NICHE_TIER_3,
    "Todos os nichos": list(NICHE_TAGS.keys()),
    "Personalizado": [],
}

CATEGORY_COLORS = {
    CATEGORY_NO_SITE: "🆕",
    CATEGORY_OPTIMIZATION: "🛠️",
    CATEGORY_DATA_BI: "📊",
}

# --------------------------------------------------------------------------
# Cabeçalho
# --------------------------------------------------------------------------
st.title("Framework - Prospecção de leads")
st.caption(
    "Prospecção de comércios locais por bairro, encontre quem precisa de "
    "site novo, otimização/segurança ou uma oferta de dados/BI."
)

# --------------------------------------------------------------------------
# Formulário de busca
# --------------------------------------------------------------------------
with st.form("busca_form"):
    col1, col2, col3 = st.columns(3)
    with col1:
        bairro = st.text_input("Bairro", placeholder="Ex.: Aquarius")
    with col2:
        cidade = st.text_input("Cidade", placeholder="Ex.: São José dos Campos")
    with col3:
        uf = st.text_input("UF (opcional)", placeholder="Ex.: SP", max_chars=2)

    preset_label = st.selectbox(
        "Quais nichos buscar?",
        options=list(PRESETS.keys()),
        index=0,
        help=(
            "'Recomendado (ICP)' usa os nichos com maior propensão real de "
            "fechar contrato, com base nos cases da SciTec Jr."
        ),
    )

    nichos_personalizados: list[str] = []
    if preset_label == "Personalizado":
        nichos_personalizados = st.multiselect(
            "Escolha os nichos", options=sorted(NICHE_TAGS.keys())
        )

    excluir_redes = st.checkbox(
        "Excluir grandes redes/franquias (ex.: Carrefour, McDonald's)",
        value=True,
        help="Foca em comércio independente — geralmente o público real do ICP.",
    )

    submitted = st.form_submit_button("🔍 Buscar leads", use_container_width=True)

# --------------------------------------------------------------------------
# Execução da busca
# --------------------------------------------------------------------------
if submitted:
    if not bairro.strip() or not cidade.strip():
        st.error("Preencha ao menos o bairro e a cidade.")
        st.stop()

    niches = (
        nichos_personalizados if preset_label == "Personalizado" else PRESETS[preset_label]
    )
    if not niches:
        st.error("Selecione ao menos um nicho.")
        st.stop()

    progress_bar = st.progress(0.0)
    status_text = st.empty()

    def _on_progress(idx: int, total: int, nome: str) -> None:
        progress_bar.progress(idx / total)
        status_text.text(f"Analisando {idx}/{total}: {nome}")

    with st.spinner("Localizando o bairro e minerando estabelecimentos..."):
        try:
            leads = run_pipeline(
                bairro=bairro.strip(),
                cidade=cidade.strip(),
                uf=uf.strip(),
                niches=niches,
                excluir_redes=excluir_redes,
                on_progress=_on_progress,
            )
        except GeocodingError as exc:
            st.error(
                f"Não foi possível localizar '{bairro}, {cidade}'. "
                f"Verifique a grafia do bairro/cidade. Detalhe técnico: {exc}"
            )
            st.stop()

    progress_bar.empty()
    status_text.empty()

    if not leads:
        st.warning(
            "Nenhum estabelecimento encontrado para esses critérios. "
            "Isso costuma acontecer quando o bairro tem poucos comércios "
            "cadastrados no OpenStreetMap — tente outro bairro ou preset."
        )
        st.stop()

    df = pd.DataFrame(leads)
    existing_cols = [c for c in COLUMN_ORDER if c in df.columns]
    remaining_cols = [c for c in df.columns if c not in existing_cols]
    df = df[existing_cols + remaining_cols]

    # ----------------------------------------------------------------
    # Resumo
    # ----------------------------------------------------------------
    st.subheader("Resumo")
    counts = df["categoria"].value_counts()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de leads", len(df))
    m2.metric(f"{CATEGORY_COLORS[CATEGORY_NO_SITE]} {CATEGORY_NO_SITE}", int(counts.get(CATEGORY_NO_SITE, 0)))
    m3.metric(f"{CATEGORY_COLORS[CATEGORY_OPTIMIZATION]} {CATEGORY_OPTIMIZATION}", int(counts.get(CATEGORY_OPTIMIZATION, 0)))
    m4.metric(f"{CATEGORY_COLORS[CATEGORY_DATA_BI]} {CATEGORY_DATA_BI}", int(counts.get(CATEGORY_DATA_BI, 0)))

    # ----------------------------------------------------------------
    # Filtro rápido por categoria + tabela
    # ----------------------------------------------------------------
    st.subheader("Leads encontrados")
    categoria_filtro = st.multiselect(
        "Filtrar por categoria",
        options=list(counts.index),
        default=list(counts.index),
    )
    df_filtrado = df[df["categoria"].isin(categoria_filtro)]

    st.dataframe(df_filtrado, use_container_width=True, hide_index=True)

    # ----------------------------------------------------------------
    # Download
    # ----------------------------------------------------------------
    csv_bytes = df_filtrado.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "⬇️ Baixar CSV",
        data=csv_bytes,
        file_name=f"leads_{bairro.strip().lower().replace(' ', '_')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
