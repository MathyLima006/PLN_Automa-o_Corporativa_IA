"""NEXA CORPORATE INTELLIGENCE - SPRINT 2

Como executar:
    pip install streamlit pandas plotly
    streamlit run app_nexa_v2.py

Pasta esperada:
    app_nexa_v2.py
    data/feedback_clientes.csv
    data/feedback_colaboradores.csv
    data/ocorrencias_operacionais.csv

Este protótipo usa dados sintéticos e regras simples de análise de texto.
Não utiliza modelo de linguagem nem conexão com MongoDB nesta versão.
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd
import plotly.express as px
import streamlit as st


# ============================================================
# 1. CONFIGURAÇÃO GERAL
# ============================================================

st.set_page_config(
    page_title="Nexa | Corporate Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

PASTA_DADOS = Path(__file__).resolve().parent / "data"
ARQUIVOS = {
    "clientes": "feedback_clientes.csv",
    "pessoas": "feedback_colaboradores.csv",
    "operacoes": "ocorrencias_operacionais.csv",
}

CORES = {
    "Positivo": "#22C55E",
    "Neutro": "#94A3B8",
    "Negativo": "#EF4444",
}

STATUS_PENDENTES = {"aberto", "pendente", "em andamento"}
PRIORIDADES_ALTAS = {"alta", "critica", "urgente"}


# ============================================================
# 2. APARÊNCIA DO SISTEMA
# ============================================================

st.markdown(
    """
    <style>
    .block-container {max-width: 1480px; padding-top: 1.7rem; padding-bottom: 3rem;}
    [data-testid="stSidebar"] {background: #101a2b;}
    [data-testid="stSidebar"] * {color: #e5eaf4;}
    div[data-testid="stMetric"] {
        background: #18253a; border: 1px solid #34465f;
        padding: 17px; border-radius: 13px;
    }
    div[data-testid="stMetric"] label {color: #cbd5e1 !important;}
    div[data-testid="stMetricValue"] {color: #f8fafc !important;}
    .nexa-hero {
        background: linear-gradient(115deg, #172554, #1d4ed8);
        padding: 28px; border-radius: 17px; margin-bottom: 20px;
        color: white;
    }
    .nexa-hero h1 {color: white; margin: 0; font-size: 2.1rem;}
    .nexa-hero p {color: #dbeafe; margin: 10px 0 0;}
    .nexa-tag {color: #94a3b8; font-size: 0.85rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 3. LEITURA E VALIDAÇÃO DOS ARQUIVOS
# ============================================================

@st.cache_data(show_spinner="Carregando bases de dados...")
def carregar_dados():
    """Abre os três CSVs e converte as colunas de data quando existirem."""
    resultado = {}

    for area, arquivo in ARQUIVOS.items():
        caminho = PASTA_DADOS / arquivo
        if not caminho.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")

        # utf-8-sig aceita arquivos UTF-8 com ou sem BOM.
        try:
            tabela = pd.read_csv(caminho, encoding="utf-8-sig")
        except UnicodeDecodeError:
            tabela = pd.read_csv(caminho, encoding="latin-1")

        # Detecta CSV separado por ponto e vírgula, comum no Excel brasileiro.
        if len(tabela.columns) == 1 and ";" in str(tabela.columns[0]):
            try:
                tabela = pd.read_csv(caminho, sep=";", encoding="utf-8-sig")
            except UnicodeDecodeError:
                tabela = pd.read_csv(caminho, sep=";", encoding="latin-1")

        tabela.columns = tabela.columns.str.strip()
        for coluna in ("data", "data_abertura", "data_resolucao"):
            if coluna in tabela.columns:
                tabela[coluna] = pd.to_datetime(tabela[coluna], errors="coerce")

        resultado[area] = tabela

    return resultado


def verificar_colunas(dados):
    """Informa claramente se faltar uma coluna indispensável."""
    necessarias = {
        "clientes": ["texto"],
        "pessoas": ["texto"],
        "operacoes": [],
    }
    erros = []
    for area, colunas in necessarias.items():
        for coluna in colunas:
            if coluna not in dados[area].columns:
                erros.append(f"{ARQUIVOS[area]}: falta a coluna '{coluna}'")
    return erros


try:
    dados = carregar_dados()
except Exception as erro:
    st.error(f"Não foi possível abrir os arquivos: {erro}")
    st.info("Confira se a pasta 'data' está ao lado deste arquivo Python e contém os três CSVs.")
    st.stop()

problemas = verificar_colunas(dados)
if problemas:
    st.error("Problemas encontrados nas colunas dos arquivos:")
    for problema in problemas:
        st.write("-", problema)
    st.stop()


# ============================================================
# 4. ANÁLISE SIMPLES DE SENTIMENTOS
# ============================================================

PALAVRAS_POSITIVAS = {
    "otimo", "excelente", "bom", "boa", "rapido", "rapida", "eficiente",
    "satisfeito", "satisfeita", "elogio", "resolveu", "resolvido",
    "resolvida", "organizado", "organizada", "melhorou", "positivo",
    "positiva", "recomendo", "agradavel", "atencioso", "atenciosa",
}

PALAVRAS_NEGATIVAS = {
    "ruim", "pessimo", "pessima", "demora", "demorado", "demorada",
    "problema", "problemas", "erro", "erros", "falha", "falhas",
    "reclamacao", "insatisfeito", "insatisfeita", "atraso", "atrasos",
    "dificil", "lento", "lenta", "negativo", "negativa", "defeito",
    "indisponivel", "confuso", "confusa", "inadequado", "inadequada",
}


def normalizar(texto):
    """Remove acentos e deixa o texto em letras minúsculas."""
    texto = str(texto).lower()
    texto = unicodedata.normalize("NFD", texto)
    return "".join(letra for letra in texto if unicodedata.category(letra) != "Mn")


def classificar_sentimento(texto):
    """Conta palavras de cada grupo; não é um modelo de inteligência artificial."""
    palavras = re.findall(r"[a-z]+", normalizar(texto))
    positivos = sum(palavra in PALAVRAS_POSITIVAS for palavra in palavras)
    negativos = sum(palavra in PALAVRAS_NEGATIVAS for palavra in palavras)

    if positivos > negativos:
        return "Positivo"
    if negativos > positivos:
        return "Negativo"
    return "Neutro"


def adicionar_sentimento(tabela):
    """Cria uma nova coluna sem modificar a tabela original."""
    tabela = tabela.copy()
    tabela["sentimento"] = tabela["texto"].fillna("").apply(classificar_sentimento)
    return tabela


clientes = adicionar_sentimento(dados["clientes"])
pessoas = adicionar_sentimento(dados["pessoas"])
operacoes = dados["operacoes"].copy()


# ============================================================
# 5. FUNÇÕES DE FILTROS
# ============================================================

def filtro_opcoes(tabela, coluna, titulo, chave):
    """Exibe multiseleção somente se a coluna existir."""
    if coluna not in tabela.columns:
        st.caption(f"Filtro '{titulo}' indisponível nesta base.")
        return tabela

    opcoes = sorted(tabela[coluna].dropna().astype(str).unique().tolist())
    selecionadas = st.multiselect(titulo, opcoes, key=chave)
    if selecionadas:
        return tabela[tabela[coluna].astype(str).isin(selecionadas)]
    return tabela


def filtro_periodo(tabela, coluna, chave):
    """Permite escolher um intervalo de datas, sem obrigar o usuário."""
    if coluna not in tabela.columns:
        return tabela
    datas = tabela[coluna].dropna()
    if datas.empty:
        return tabela

    minimo = datas.min().date()
    maximo = datas.max().date()
    periodo = st.date_input(
        "Período", value=(minimo, maximo),
        min_value=minimo, max_value=maximo, key=chave,
    )
    if isinstance(periodo, (tuple, list)) and len(periodo) == 2:
        return tabela[tabela[coluna].dt.date.between(periodo[0], periodo[1])]
    return tabela


def aplicar_filtros(tabela, campos, prefixo, coluna_data=None):
    """Cria uma linha de filtros e devolve somente os registros selecionados."""
    filtrada = tabela.copy()
    colunas = st.columns(len(campos) + (1 if coluna_data else 0))

    for indice, (campo, titulo) in enumerate(campos):
        with colunas[indice]:
            filtrada = filtro_opcoes(filtrada, campo, titulo, f"{prefixo}_{campo}")

    if coluna_data:
        with colunas[-1]:
            filtrada = filtro_periodo(filtrada, coluna_data, f"{prefixo}_periodo")
    return filtrada


# ============================================================
# 6. FUNÇÕES DE GRÁFICOS E TABELAS
# ============================================================

def grafico_sentimento(tabela, titulo):
    """Gráfico de rosca com sentimentos positivos, neutros e negativos."""
    if tabela.empty:
        st.info("Nenhum registro para os filtros escolhidos.")
        return

    ordem = ["Positivo", "Neutro", "Negativo"]
    resumo = tabela["sentimento"].value_counts().reindex(ordem, fill_value=0)
    grafico = pd.DataFrame({"Sentimento": ordem, "Quantidade": resumo.values})
    fig = px.pie(
        grafico, names="Sentimento", values="Quantidade", hole=0.58,
        color="Sentimento", color_discrete_map=CORES, title=titulo,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(margin=dict(t=55, b=15, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)


def grafico_barras(tabela, coluna, titulo, limite=10):
    """Conta quantos registros existem em cada categoria."""
    if tabela.empty or coluna not in tabela.columns:
        st.info("Sem dados disponíveis para este gráfico.")
        return

    contagem = tabela[coluna].fillna("Não informado").astype(str).value_counts().head(limite)
    resumo = contagem.rename_axis("Categoria").reset_index(name="Quantidade")
    fig = px.bar(
        resumo, x="Categoria", y="Quantidade", text="Quantidade",
        title=titulo, color_discrete_sequence=["#3B82F6"],
    )
    fig.update_layout(xaxis_title="", margin=dict(t=55, b=15, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)


def grafico_temporal(tabela, coluna, titulo):
    """Mostra a quantidade de registros por mês."""
    if tabela.empty or coluna not in tabela.columns:
        st.info("Sem datas disponíveis para este gráfico.")
        return

    validos = tabela.dropna(subset=[coluna]).copy()
    if validos.empty:
        st.info("Nenhuma data válida para exibir.")
        return

    validos["Mês"] = validos[coluna].dt.to_period("M").astype(str)
    resumo = validos.groupby("Mês").size().reset_index(name="Registros")
    fig = px.line(resumo, x="Mês", y="Registros", markers=True, title=titulo)
    fig.update_layout(margin=dict(t=55, b=15, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)


def tabela_exportavel(tabela, nome):
    """Exibe a tabela e permite baixar os resultados filtrados."""
    with st.expander(f"📋 Visualizar registros ({len(tabela)})"):
        st.dataframe(tabela, use_container_width=True, hide_index=True)
        arquivo = tabela.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "⬇️ Baixar registros em CSV", data=arquivo,
            file_name=nome, mime="text/csv", key=f"download_{nome}",
        )


def quantidade(tabela, coluna, valores):
    """Conta registros de uma coluna sem diferenciar maiúsculas e acentos."""
    if coluna not in tabela.columns:
        return 0
    serie = tabela[coluna].fillna("").astype(str).map(normalizar).str.strip()
    return int(serie.isin(valores).sum())


def metricas_sentimento(tabela, rotulo="Feedbacks"):
    """Mostra três indicadores na mesma linha."""
    c1, c2, c3 = st.columns(3)
    c1.metric(rotulo, len(tabela))
    c2.metric("Positivos", int((tabela["sentimento"] == "Positivo").sum()))
    c3.metric("Negativos", int((tabela["sentimento"] == "Negativo").sum()))


# ============================================================
# 7. ALERTAS E RECOMENDAÇÕES
# ============================================================

def recomendacao_feedback(tabela, tipo):
    """Gera sugestões simples a partir da proporção de registros negativos."""
    if tabela.empty:
        st.info("Selecione outros filtros para gerar recomendações.")
        return

    negativos = int((tabela["sentimento"] == "Negativo").sum())
    percentual = 100 * negativos / len(tabela)

    if percentual >= 30:
        st.warning(f"Atenção: {percentual:.1f}% dos feedbacks filtrados foram classificados como negativos.")
    elif percentual >= 15:
        st.info(f"Monitoramento: {percentual:.1f}% dos feedbacks filtrados foram negativos.")
    else:
        st.success(f"O percentual de feedbacks negativos filtrados é {percentual:.1f}%.")

    if tipo == "clientes":
        st.write("**Sugestão:** revisar os comentários negativos e identificar problemas recorrentes no atendimento ou nos serviços.")
    else:
        st.write("**Sugestão:** avaliar os relatos dos colaboradores e discutir oportunidades de melhoria com os departamentos envolvidos.")
    st.caption("Os limites percentuais são regras ilustrativas, não metas oficiais da empresa.")


def recomendacao_operacoes(tabela):
    """Destaca registros que merecem investigação operacional."""
    if tabela.empty:
        st.info("Nenhuma ocorrência encontrada para os filtros atuais.")
        return

    pendentes = quantidade(tabela, "status", STATUS_PENDENTES)
    altas = quantidade(tabela, "prioridade", PRIORIDADES_ALTAS)
    if pendentes:
        st.warning(f"Existem {pendentes} ocorrências não concluídas no recorte selecionado.")
    else:
        st.success("Não foram identificadas ocorrências pendentes nos registros filtrados.")
    if altas:
        st.write(f"**Prioridade de análise:** verificar as {altas} ocorrências marcadas como alta, crítica ou urgente.")
    st.caption("Recomendações automáticas por regras simples; exigem avaliação humana.")


def resumo_alertas():
    """Exibe um panorama rápido dos pontos que exigem atenção."""
    neg_clientes = int((clientes["sentimento"] == "Negativo").sum())
    neg_pessoas = int((pessoas["sentimento"] == "Negativo").sum())
    pendentes = quantidade(operacoes, "status", STATUS_PENDENTES)

    st.subheader("🔎 Pontos de atenção")
    a, b, c = st.columns(3)
    a.metric("Clientes insatisfeitos (registros)", neg_clientes)
    b.metric("Feedbacks negativos internos", neg_pessoas)
    c.metric("Ocorrências não concluídas", pendentes)
    st.caption("Contagens demonstrativas; um registro negativo não equivale necessariamente a uma pessoa única.")


# ============================================================
# 8. MENU LATERAL
# ============================================================

st.sidebar.title("NEXA")
st.sidebar.caption("CORPORATE INTELLIGENCE")
st.sidebar.divider()

pagina = st.sidebar.radio(
    "Navegação",
    ["Visão Geral", "Clientes", "Pessoas", "Operações", "Assistente IA"],
)

st.sidebar.divider()
st.sidebar.caption("Sprint Dois • Protótipo acadêmico")
st.sidebar.caption("Bases sintéticas • Análise textual por regras")


# ============================================================
# 9. PÁGINA: VISÃO GERAL
# ============================================================

if pagina == "Visão Geral":
    st.markdown(
        """
        <div class="nexa-hero">
            <h1>Corporate Intelligence</h1>
            <p>Informações de clientes, colaboradores e operações em um só lugar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    total = len(clientes) + len(pessoas) + len(operacoes)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de registros", f"{total:,}".replace(",", "."))
    c2.metric("Feedbacks de clientes", len(clientes))
    c3.metric("Feedbacks de colaboradores", len(pessoas))
    c4.metric("Ocorrências operacionais", len(operacoes))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        grafico_sentimento(clientes, "Sentimento dos clientes")
    with c2:
        grafico_sentimento(pessoas, "Sentimento dos colaboradores")

    c1, c2 = st.columns(2)
    with c1:
        grafico_temporal(clientes, "data", "Evolução dos feedbacks de clientes")
    with c2:
        grafico_temporal(operacoes, "data_abertura", "Evolução das ocorrências")

    st.divider()
    resumo_alertas()
    st.info("Use o menu lateral para explorar os dados e investigar cada área separadamente.")


# ============================================================
# 10. PÁGINA: CLIENTES
# ============================================================

elif pagina == "Clientes":
    st.title("👥 Experiência do Cliente")
    st.write("Explore comentários recebidos, canais de atendimento e produtos ou serviços.")

    filtrados = aplicar_filtros(
        clientes,
        [("canal", "Canal"), ("produto_servico", "Produto ou serviço"),
         ("sentimento", "Sentimento")],
        "clientes", coluna_data="data",
    )

    st.divider()
    metricas_sentimento(filtrados, "Feedbacks encontrados")
    c1, c2 = st.columns(2)
    with c1:
        grafico_sentimento(filtrados, "Distribuição dos sentimentos")
    with c2:
        grafico_barras(filtrados, "canal", "Feedbacks por canal")

    st.subheader("💡 Interpretação dos resultados")
    recomendacao_feedback(filtrados, "clientes")
    tabela_exportavel(filtrados, "clientes_filtrados.csv")


# ============================================================
# 11. PÁGINA: PESSOAS
# ============================================================

elif pagina == "Pessoas":
    st.title("🧑‍💼 Inteligência de Pessoas")
    st.write("Investigue as percepções dos colaboradores sobre o ambiente de trabalho.")

    filtrados = aplicar_filtros(
        pessoas,
        [("departamento", "Departamento"),
         ("categoria_informada", "Categoria"), ("sentimento", "Sentimento")],
        "pessoas", coluna_data="data",
    )

    st.divider()
    metricas_sentimento(filtrados, "Feedbacks encontrados")
    c1, c2 = st.columns(2)
    with c1:
        grafico_sentimento(filtrados, "Sentimento dos colaboradores")
    with c2:
        grafico_barras(filtrados, "departamento", "Feedbacks por departamento")

    st.subheader("💡 Interpretação dos resultados")
    recomendacao_feedback(filtrados, "pessoas")
    tabela_exportavel(filtrados, "pessoas_filtradas.csv")


# ============================================================
# 12. PÁGINA: OPERAÇÕES
# ============================================================

elif pagina == "Operações":
    st.title("⚙️ Eficiência Operacional")
    st.write("Monitore ocorrências, prioridades e processos que exigem atenção.")

    filtrados = aplicar_filtros(
        operacoes,
        [("departamento", "Departamento"), ("prioridade", "Prioridade"),
         ("status", "Status")],
        "operacoes", coluna_data="data_abertura",
    )

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Ocorrências encontradas", len(filtrados))
    c2.metric("Alta prioridade", quantidade(filtrados, "prioridade", PRIORIDADES_ALTAS))
    c3.metric("Não concluídas", quantidade(filtrados, "status", STATUS_PENDENTES))

    c1, c2 = st.columns(2)
    with c1:
        grafico_barras(filtrados, "prioridade", "Ocorrências por prioridade")
    with c2:
        grafico_barras(filtrados, "processo", "Processos com mais ocorrências")

    grafico_temporal(filtrados, "data_abertura", "Ocorrências ao longo do tempo")
    st.subheader("💡 Interpretação dos resultados")
    recomendacao_operacoes(filtrados)
    tabela_exportavel(filtrados, "operacoes_filtradas.csv")


# ============================================================
# 13. PÁGINA: ASSISTENTE DEMONSTRATIVO
# ============================================================

elif pagina == "Assistente IA":
    st.title("🤖 Assistente de Inteligência Corporativa")
    st.write("Digite uma pergunta para receber um resumo simples dos dados carregados.")
    st.info(
        "Este assistente ainda não utiliza IA generativa ou modelo de linguagem. "
        "As respostas são produzidas por regras programadas."
    )

    pergunta = st.text_area(
        "Qual análise você deseja realizar?",
        placeholder="Ex.: Como está a satisfação dos clientes?",
        height=110,
    )

    if st.button("Analisar dados", type="primary"):
        if not pergunta.strip():
            st.warning("Digite uma pergunta para continuar.")
        else:
            consulta = normalizar(pergunta)
            st.divider()

            if any(termo in consulta for termo in ("cliente", "satisfacao", "consumidor")):
                st.subheader("Análise de clientes")
                metricas_sentimento(clientes, "Feedbacks de clientes")
                grafico_sentimento(clientes, "Panorama dos clientes")
                recomendacao_feedback(clientes, "clientes")

            elif any(termo in consulta for termo in ("colaborador", "funcionario", "equipe", "clima", "pessoas")):
                st.subheader("Análise de pessoas")
                metricas_sentimento(pessoas, "Feedbacks de colaboradores")
                grafico_sentimento(pessoas, "Panorama dos colaboradores")
                recomendacao_feedback(pessoas, "pessoas")

            elif any(termo in consulta for termo in ("operacao", "ocorrencia", "processo", "prioridade", "falha")):
                st.subheader("Análise operacional")
                c1, c2, c3 = st.columns(3)
                c1.metric("Ocorrências", len(operacoes))
                c2.metric("Não concluídas", quantidade(operacoes, "status", STATUS_PENDENTES))
                c3.metric("Alta prioridade", quantidade(operacoes, "prioridade", PRIORIDADES_ALTAS))
                grafico_barras(operacoes, "status", "Ocorrências por status")
                recomendacao_operacoes(operacoes)

            else:
                st.subheader("Resumo geral")
                st.write(
                    f"A base possui **{len(clientes)} feedbacks de clientes**, "
                    f"**{len(pessoas)} feedbacks de colaboradores** e "
                    f"**{len(operacoes)} ocorrências operacionais**."
                )
                resumo_alertas()
                st.write(
                    "Para uma análise específica, mencione clientes, satisfação, "
                    "colaboradores, clima, operações, processos ou prioridades."
                )

            st.caption("Resultados exploratórios gerados com dados sintéticos e regras demonstrativas.")
