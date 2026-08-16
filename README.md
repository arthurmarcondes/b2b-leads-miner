# 🎯 B2B Leads Miner — Prospecção Inteligente de Comércios Locais

> Pipeline de **Data Mining** em Python que minera estabelecimentos comerciais de um bairro, audita a saúde técnica dos seus sites e classifica cada um em uma oferta comercial acionável — **sem depender de nenhuma API paga**.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Status](https://img.shields.io/badge/status-portfolio--ready-brightgreen)]()

---

## 📌 Sumário

- [Objetivo do Projeto](#-objetivo-do-projeto)
- [Como Funciona (Teoria)](#-como-funciona-teoria-por-trás-da-mineração)
- [Arquitetura](#-arquitetura)
- [Estrutura de Pastas](#-estrutura-de-pastas)
- [Interface Web (sem terminal, sem código)](#️-interface-web-sem-terminal-sem-código)
- [Instalação (via CLI)](#️-instalação-via-cli)
- [Como Usar (CLI)](#-como-usar-cli)
- [Exemplo de Saída](#-exemplo-de-saída)
- [Regras de Classificação](#-regras-de-classificação)
- [Utilidade Prática](#-utilidade-prática-para-quem-serve)
- [Testes](#-testes)
- [Limitações e Ética](#-limitações-e-considerações-éticas)
- [Roadmap](#-roadmap)

---

## 🎯 Objetivo do Projeto

Agências de marketing digital, freelancers de desenvolvimento web e consultores de BI gastam um tempo enorme em **prospecção manual**: procurar comércios de um bairro no Google Maps, abrir um por um, checar se o site existe, se carrega rápido, se tem cadeado (HTTPS) — tudo isso à mão.

Este projeto **automatiza esse funil inteiro**. Você informa um bairro e um conjunto de nichos de mercado (restaurantes, salões, academias, clínicas, etc.) e o pipeline devolve uma planilha CSV com cada estabelecimento já **pré-qualificado** em uma de três frentes de venda:

| Categoria | Significado | Oferta comercial sugerida |
|---|---|---|
| 🆕 **Criar Site do Zero** | Empresa sem website (ou sem presença própria cadastrada) | Venda de site institucional / landing page |
| 🛠️ **Otimização / Segurança** | Site existe, mas tem erro HTTP, sem HTTPS válido ou está lento | Venda de manutenção, migração de SSL, otimização de performance |
| 📊 **Análise de Dados / BI** | Site rápido, seguro e saudável | Venda de dashboards, analytics, automações e integrações de dados |

---

## 🧠 Como Funciona (Teoria por trás da Mineração)

O projeto segue um pipeline clássico de **ETL + regras de negócio**, dividido em 4 estágios:

```
┌─────────────────┐     ┌──────────────────┐     ┌────────────────────┐     ┌───────────────┐
│  1. MINERAÇÃO    │ --> │  2. ANÁLISE       │ --> │  3. CLASSIFICAÇÃO   │ --> │  4. EXPORTAÇÃO │
│  Geocodificação  │     │  Requisição HTTP   │     │  Regras de negócio  │     │  CSV + Resumo  │
│  + Overpass API  │     │  real ao site       │     │  (funil de vendas)  │     │  (pandas)      │
└─────────────────┘     └──────────────────┘     └────────────────────┘     └───────────────┘
```

### 1. Mineração (Data Mining Geoespacial)
O bairro informado é **geocodificado** via [Nominatim](https://nominatim.org/) (serviço público do OpenStreetMap), retornando uma *bounding box* (retângulo de coordenadas). Em seguida, a [Overpass API](https://overpass-api.de/) é consultada dentro dessa bounding box, filtrando por tags específicas (`amenity=restaurant`, `shop=hairdresser`, `office=lawyer`, etc.) — o equivalente a "buscar todos os restaurantes cadastrados dentro deste retângulo do mapa".

> **Por que OpenStreetMap em vez de Google Places?** Porque é gratuito, sem limite de cota, sem necessidade de cartão de crédito/API key — ideal para portfólio e para rodar localmente sem custos. A arquitetura é modular o suficiente (veja `src/overpass_client.py`) para trocar essa fonte por Google Places API, SerpApi ou qualquer outra no futuro sem alterar o resto do pipeline.

### 2. Análise Técnica (Auditoria de Sites)
Para cada estabelecimento que possui um campo `website` cadastrado, o módulo `SiteAnalyzer` faz uma requisição HTTP real usando `requests.Session()` (reaproveitando conexões TCP/TLS para eficiência) e mede:

- **Disponibilidade**: o site respondeu ou deu timeout/erro de conexão?
- **Status HTTP**: a resposta foi 2xx/3xx (saudável) ou 4xx/5xx (erro)?
- **HTTPS/SSL**: a conexão final foi HTTPS com certificado válido?
- **Latência**: quanto tempo (em segundos) o servidor levou para responder?

### 3. Classificação (Regras de Negócio)
O módulo `LeadClassifier` aplica um conjunto de regras determinísticas (documentadas em detalhe na seção [Regras de Classificação](#-regras-de-classificação)) que transformam os sinais técnicos brutos em uma **categoria de oferta comercial**.

### 4. Exportação
O módulo `DataExporter` consolida tudo em um `pandas.DataFrame`, salva em CSV (pronto para importar em CRM, Google Sheets ou Excel) e imprime um resumo estatístico no console.

---

## 🏗️ Arquitetura

O projeto segue o princípio de **separação de responsabilidades** (Single Responsibility Principle): cada módulo tem uma única razão para mudar.

```
config/settings.py     -> "O QUE" buscar (nichos, thresholds) — muda sem tocar em lógica
src/overpass_client.py -> "ONDE" encontrar os leads (mineração geoespacial)
src/site_analyzer.py   -> "COMO" está o site (análise técnica pura, sem regra de negócio)
src/lead_classifier.py -> "O QUE FAZER" com o lead (regra de negócio pura, sem I/O de rede)
src/data_exporter.py   -> "ONDE SALVAR" o resultado (persistência)
main.py                -> Orquestração via CLI (argparse)
```

Essa separação permite, por exemplo, trocar a fonte de dados (`overpass_client.py`) por uma API paga sem tocar em uma linha da lógica de classificação, ou recalibrar os thresholds de lentidão em `config/settings.py` sem mexer em código.

---

## 📁 Estrutura de Pastas

```
b2b-leads-miner/
├── README.md
├── requirements.txt
├── .gitignore
├── main.py                      # Ponto de entrada CLI
├── app.py                       # Interface web (Streamlit) — sem terminal/código
│
├── config/
│   ├── __init__.py
│   └── settings.py              # Nichos, thresholds, constantes, presets de ICP
│
├── src/
│   ├── __init__.py
│   ├── logger.py                # Logging centralizado (console + arquivo)
│   ├── overpass_client.py       # Mineração via Nominatim + Overpass API
│   ├── site_analyzer.py         # Análise técnica de sites (HTTP/HTTPS/latência)
│   ├── lead_classifier.py       # Regras de negócio de classificação
│   ├── pipeline.py              # Orquestração compartilhada entre main.py e app.py
│   └── data_exporter.py         # Exportação para CSV via pandas
│
├── tests/
│   ├── __init__.py
│   └── test_lead_classifier.py  # Testes unitários das regras de negócio
│
├── output/                      # CSVs gerados via CLI (ignorado no git, exceto .gitkeep)
│   └── .gitkeep
│
└── logs/                        # Logs de execução (ignorado no git, exceto .gitkeep)
    └── .gitkeep
```

---

## 🖥️ Interface Web (sem terminal, sem código)

Para que qualquer pessoa da equipe (comercial, vendas) use a ferramenta sem precisar abrir o VS Code ou digitar comandos, o projeto inclui uma interface web construída com [Streamlit](https://streamlit.io/) (`app.py`): um formulário no navegador com campos de bairro/cidade/nichos, botão "Buscar", tabela de resultado na tela e botão de download do CSV.

### Opção A — Rodar localmente (você mantém o link ativo na sua máquina)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Isso abre automaticamente uma aba no navegador (`http://localhost:8501`) com o formulário pronto para uso — quem for usar só precisa desse link enquanto o comando estiver rodando na sua máquina.

### Opção B — Publicar uma URL pública gratuita (recomendado para o time todo)

1. Suba este repositório no GitHub (público ou privado).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e conecte sua conta GitHub.
3. Clique em "New app", aponte para o repositório e selecione o arquivo `app.py`.
4. Em poucos minutos você recebe uma URL pública (ex.: `seu-app.streamlit.app`) — qualquer pessoa da equipe abre esse link no navegador e usa a ferramenta, sem instalar Python, sem terminal, sem VS Code.

> **Nota**: a hospedagem gratuita do Streamlit Community Cloud "dorme" após um tempo sem uso e demora alguns segundos para acordar no primeiro acesso — normal e sem custo.

---

## ⚙️ Instalação (via CLI)

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/b2b-leads-miner.git
cd b2b-leads-miner

# 2. Crie e ative um ambiente virtual
python3 -m venv venv
source venv/bin/activate      # Linux/Mac
venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt
```

**Requisitos**: Python 3.10+ (usa sintaxe moderna de type hints como `list[str]` e `tuple[...]`).

---

## 🚀 Como Usar (CLI)

### Buscar o preset recomendado (ICP)

Por padrão, o comando já usa o preset `icp` — os nichos com maior propensão real de fechar contrato, com base nos cases do portfólio da SciTec Jr. (comércio de produto físico + serviços com agendamento):

```bash
python main.py --bairro "Aquarius" --cidade "São José dos Campos" --uf SP --excluir-redes
```

### Buscar nichos específicos

```bash
python main.py \
    --bairro "Aquarius" \
    --cidade "São José dos Campos" \
    --uf SP \
    --nichos loja_roupas,loja_presentes,papelaria,joalheria \
    --excluir-redes
```

### Buscar todos os nichos cadastrados

```bash
python main.py --bairro "Aquarius" --cidade "São José dos Campos" --uf SP --nichos todos
```

### Argumentos disponíveis

| Argumento | Obrigatório | Descrição |
|---|---|---|
| `--bairro` | ✅ | Nome do bairro alvo (ex.: `"Aquarius"`) |
| `--cidade` | ✅ | Cidade correspondente (ex.: `"São José dos Campos"`) |
| `--uf` | ❌ | Sigla do estado — melhora a precisão da geocodificação |
| `--nichos` | ❌ (default: `icp`) | Lista separada por vírgula, um preset (`icp`, `produto`, `servico`, `todos`) ou `listar` |
| `--excluir-redes` | ❌ | Remove grandes redes/franquias (ex.: Carrefour), focando em comércio independente |

O resultado é salvo em `output/leads_<bairro>_<timestamp>.csv`.

---

## 📊 Exemplo de Saída

Console:
```
==================================================
RESUMO DA PROSPECÇÃO
==================================================
  Criar Site do Zero                12 leads  ( 46.2%)
  Otimização / Segurança             9 leads  ( 34.6%)
  Análise de Dados / BI              5 leads  ( 19.2%)
--------------------------------------------------
  TOTAL                             26 leads
==================================================
```

CSV (`output/leads_aquarius_20260813_210500.csv`):

| nome | nicho | categoria | website | status_code | is_https | response_time_seconds | motivos |
|---|---|---|---|---|---|---|---|
| Padaria Bela Vista | padaria | Criar Site do Zero | | | | | Nenhum website cadastrado... |
| Oficina do Zé | oficina_mecanica | Otimização / Segurança | http://oficinadoze.com | 200 | False | 4.21 | Sem HTTPS válido... \| Tempo de resposta lento... |
| Clínica Vida Nova | clinica_medica | Análise de Dados / BI | https://clinicavidanova.com | 200 | True | 0.38 | Site rápido, seguro... |

---

## 🎯 ICP (Ideal Customer Profile)

A curadoria de nichos em `config/settings.py` não é arbitrária — reflete o perfil de cliente que historicamente fecha contrato, com base nos cases reais do portfólio da SciTec Jr. (Miah Moda, Ustyle, Sansomed):

| Prioridade | Perfil | Por quê | Nichos |
|---|---|---|---|
| 🥇 1 | Comércio de produto físico | Candidato natural a e-commerce — é literalmente o que a empresa já entrega e sabe vender | `loja_roupas`, `loja_calcados`, `loja_presentes`, `papelaria`, `armarinho`, `loja_moveis`, `joalheria`, `loja_bebes`, `loja_brinquedos`, `otica`, `petshop`, `loja_eletronicos` |
| 🥈 2 | Serviço com agendamento/gestão de cliente | Precisa de sistema de marcação, carteira de clientes, dashboard — abre porta para BI também | `salao_beleza`, `academia`, `imobiliaria`, `farmacia` |
| 🥉 3 | Serviço profissional | Presença digital ajuda a captar contrato maior, mas menor propensão | `advocacia`, `contabilidade`, `clinica_odontologica`, `clinica_medica`, `oficina_mecanica`, `lanchonete` |
| ❌ Fora do ICP | Delivery de comida | Já resolveu presença digital via iFood/Rappi — baixa propensão a fechar site próprio | *(removido: restaurante)* |

O preset `--nichos icp` (default) usa as prioridades 1+2. Use `--nichos produto` para focar só na prioridade 1, ou `--nichos todos` para incluir também a prioridade 3.

---

## 📐 Regras de Classificação

A classificação segue ordem de precedência: primeiro verifica-se ausência de site; depois, problemas técnicos; por fim, saúde plena.

```
SE não tem website
    -> "Criar Site do Zero"

SENÃO SE (status HTTP >= 400)
      OU (não é HTTPS válido)
      OU (tempo de resposta > 2.5s)
      OU (timeout / site fora do ar)
    -> "Otimização / Segurança"

SENÃO
    -> "Análise de Dados / BI"
```

Os thresholds (ex.: `2.5s` para lentidão) são configuráveis em `config/settings.py` sem necessidade de alterar código de lógica.

---

## 💼 Utilidade Prática (Para Quem Serve)

- **Agências de web design**: lista pronta de empresas sem site num bairro específico — lead list para prospecção fria com abertura natural ("notei que sua empresa não tem site...").
- **Freelancers de segurança/performance**: leads com sites lentos ou sem HTTPS são um pitch imediato ("seu site está sem certificado de segurança, isso afeta o SEO e a confiança do cliente").
- **Consultores de BI/Data**: empresas com sites saudáveis já têm maturidade digital suficiente para investir em dashboards, automações de WhatsApp, integrações com CRM, etc.
- **Estudos de mercado**: mapeamento da maturidade digital de um bairro/região inteira, útil para relatórios e planejamento comercial territorial.

---

## 🧪 Testes

```bash
python -m unittest discover -s tests -v
```

Os testes cobrem a camada de regras de negócio (`LeadClassifier`) de forma isolada, sem dependência de rede — usando resultados de análise sintéticos (`SiteAnalysisResult`).

---

## ⚠️ Limitações e Considerações Éticas

- **Cobertura de dados**: a qualidade dos resultados depende do quão completo é o cadastro do bairro no OpenStreetMap. Bairros pouco mapeados retornarão menos (ou nenhum) resultado — nesse caso, considere integrar uma fonte paga (Google Places API) seguindo a mesma interface de `overpass_client.py`.
- **Rate limiting**: o Nominatim exige no máximo 1 requisição/segundo e um `User-Agent` identificável — já respeitado no código (`NOMINATIM_RATE_LIMIT_SECONDS`). **Edite o `USER_AGENT` em `config/settings.py` com seu contato real antes de uso intensivo.**
- **Uso responsável**: este projeto acessa apenas dados públicos (OSM) e realiza requisições HTTP padrão (equivalentes a abrir o site no navegador) para checar disponibilidade — não realiza scraping de conteúdo protegido, não burla autenticação nem CAPTCHAs, e respeita timeouts razoáveis para não sobrecarregar os servidores analisados.
- **LGPD**: os dados minerados (nome comercial, endereço, telefone público, website) são informações institucionais públicas de pessoas jurídicas, não dados pessoais sensíveis. Ainda assim, use a ferramenta de forma responsável e em conformidade com a legislação aplicável ao seu caso de uso comercial.

---

## 🗺️ Roadmap

- [ ] Adaptador opcional para Google Places API (fonte alternativa/complementar ao OSM)
- [ ] Análise de performance com Lighthouse/PageSpeed Insights API
- [ ] Exportação direta para Google Sheets via `gspread`
- [ ] Dashboard interativo (Streamlit) para visualizar os leads no mapa
- [ ] Enriquecimento com dados de redes sociais (Instagram Business)

---

## 📄 Licença

Distribuído sob a licença MIT. Sinta-se livre para usar, modificar e adaptar este projeto.

---

<p align="center">Desenvolvido como projeto de portfólio em Engenharia de Software / Ciência de Dados.</p>
