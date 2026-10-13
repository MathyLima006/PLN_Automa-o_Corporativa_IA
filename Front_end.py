
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# CONFIGURAÇÃO
# =========================================================

st.set_page_config(
    page_title="Nexa | Corporate Intelligence",
    page_icon="📊",
    layout="wide",
)

DATA_DIR = Path(__file__).parent / "data"

ARQUIVOS = {
    "clientes": "feedback_clientes.csv",
    "pessoas": "feedback_colaboradores.csv",
    "operacoes": "ocorrencias_operacionais.csv",
}

# =========================================================
# ESTILO VISUAL
# =========================================================

st.markdown("""
<style>
    .block-container {
        padding-top: 1.8rem;
        padding-bottom: 2rem;
    }
    .hero {
        padding: 24px;
        border-radius: 14px;
        background: linear-gradient(115deg, #172554, #1d4ed8);
        color: white;
        margin-bottom: 22px;
    }
    .hero h1 {
        color: white;
        margin-bottom: 6px;
    }
    .hero p {
        color: #dbeafe;
        margin-bottom: 0;
    }
    div[data-testid="stMetric"] {
    background: #171b25;
    border: 1px solid #303747;
    padding: 18px;
    border-radius: 12px;
    }

    div[data-testid="stMetric"] label {
    color: #aab5c8 !important;
    }

    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #f1f5f9 !important;
    font-size: 1.8rem;
    font-weight: 700;
    }

    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    color: #94a3b8 !important;
    }
    h2, h3 {
        letter-spacing: -0.3px;
    }
    
    /* Campos de seleção */
    div[data-baseweb="select"] > div {
    background-color: #171b25;
    border: 1px solid #303747;
    border-radius: 10px;
    }

    /* Texto dos campos */
    div[data-baseweb="select"] span {
    color: #e2e8f0;
    }

    /* Etiquetas das opções selecionadas */
    div[data-baseweb="tag"] {
    background-color: #263b63 !important;
    border: 1px solid #3b5990 !important;
    border-radius: 6px !important;
    }

    div[data-baseweb="tag"] span {
    color: #eaf2ff !important;
    }

    /* Foco nos campos */
    div[data-baseweb="select"]:focus-within > div {
    border-color: #5b8def;
    box-shadow: 0 0 0 1px #5b8def;
    }
    </style>
""", unsafe_allow_html=True)

# =========================================================
# CARREGAMENTO DOS DADOS
# =========================================================

@st.cache_data
def carregar_dados():
    dados = {}

    for chave, nome in ARQUIVOS.items():
        caminho = DATA_DIR / nome

        if not caminho.exists():
            raise FileNotFoundError(
                f"Arquivo não encontrado: {caminho}"
            )

        df = pd.read_csv(caminho)

        # Converte colunas de data quando existentes
        for coluna in ["data", "data_abertura", "data_resolucao"]:
            if coluna in df.columns:
                df[coluna] = pd.to_datetime(
                    df[coluna], errors="coerce"
                )

        dados[chave] = df

    return dados


try:
    dados = carregar_dados()
except Exception as erro:
    st.error(f"Não foi possível carregar os dados: {erro}")
    st.info(
        "Confira se a pasta data contém os três arquivos CSV "
        "com os nomes esperados."
    )
    st.stop()

clientes = dados["clientes"].copy()
pessoas = dados["pessoas"].copy()
operacoes = dados["operacoes"].copy()

# =========================================================
# ANÁLISES DEMONSTRATIVAS DE TEXTO
# =========================================================

POSITIVAS = [
    "ótimo", "otimo", "excelente", "bom", "boa", "rápido",
    "rapido", "eficiente", "satisfeito", "satisfeita",
    "elogio", "resolveu", "resolvido", "resolvida",
    "organizado", "organizada", "melhorou", "positivo",
    "positiva", "recomendo", "agradável", "agradavel",
]

NEGATIVAS = [
    "ruim", "péssimo", "pessimo", "demora", "demorado",
    "demorada", "problema", "erro", "falha", "reclamação",
    "reclamacao", "insatisfeito", "insatisfeita", "atraso",
    "difícil", "dificil", "lento", "lenta", "negativo",
    "negativa", "defeito", "indisponível", "indisponivel",
]

def classificar_sentimento(texto):
    texto = str(texto).lower()
    positivos = sum(p in texto for p in POSITIVAS)
    negativos = sum(n in texto for n in NEGATIVAS)

    if positivos > negativos:
        return "Positivo"
    if negativos > positivos:
        return "Negativo"
    return "Neutro"

def adicionar_sentimento(df):
    if "texto" in df.columns:
        df["sentimento"] = df["texto"].apply(
            classificar_sentimento
        )
    else:
        df["sentimento"] = "Não classificado"
    return df

clientes = adicionar_sentimento(clientes)
pessoas = adicionar_sentimento(pessoas)


def grafico_sentimento(df, titulo):
    ordem = ["Positivo", "Neutro", "Negativo"]

    contagem = (
        df["sentimento"]
        .value_counts()
        .reindex(ordem, fill_value=0)
        .rename_axis("Sentimento")
        .reset_index(name="Quantidade")
    )

    fig = px.pie(
        contagem,
        names="Sentimento",
        values="Quantidade",
        hole=0.55,
        title=titulo,
        category_orders={"Sentimento": ordem},
        color="Sentimento",
      color_discrete_map={
    "Positivo": "#22C55E",
    "Neutro": "#94A3B8",
    "Negativo": "#EF4444",
    },
    )

    fig.update_traces(
        textinfo="percent+label",
        hovertemplate="%{label}: %{value} registros (%{percent})<extra></extra>",
    )

    fig.update_layout(
        legend_title_text="Sentimento",
        margin=dict(t=55, b=10, l=10, r=10),
    )

    return fig

def grafico_temporal(df, coluna_data, titulo):
    temporal = df.dropna(subset=[coluna_data]).copy()

    if temporal.empty:
        st.info("Não há datas válidas para montar este gráfico.")
        return

    temporal["Mês"] = (
        temporal[coluna_data].dt.to_period("M").astype(str)
    )
    resumo = (
        temporal.groupby("Mês")
        .size()
        .reset_index(name="Registros")
    )

    fig = px.line(
        resumo,
        x="Mês",
        y="Registros",
        markers=True,
        title=titulo,
    )
    fig.update_layout(margin=dict(t=55, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

def grafico_barras(df, coluna, titulo, limite=12):
    if coluna not in df.columns:
        st.info(f"A coluna '{coluna}' não está disponível.")
        return

    resumo = (
        df[coluna]
        .fillna("Não informado")
        .astype(str)
        .value_counts()
        .head(limite)
        .rename_axis("Categoria")
        .reset_index(name="Registros")
    )

    fig = px.bar(
        resumo,
        x="Categoria",
        y="Registros",
        title=titulo,
        text="Registros",
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Quantidade de registros",
        margin=dict(t=55, b=10, l=10, r=10),
    )
    st.plotly_chart(fig, use_container_width=True)

def mostrar_tabela(df, colunas=None):
    if colunas:
        colunas = [c for c in colunas if c in df.columns]
        df = df[colunas]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

def aplicar_filtro(df, coluna, valores):
    if coluna and valores and coluna in df.columns:
        return df[df[coluna].isin(valores)]
    return df

# =========================================================
# NAVEGAÇÃO
# =========================================================

st.sidebar.title("NEXA")
st.sidebar.caption("CORPORATE INTELLIGENCE")
pagina = st.sidebar.radio(
    "Navegação",
    [
        "Visão Geral",
        "Clientes",
        "Pessoas",
        "Operações",
        "Assistente IA",
    ],
)
st.sidebar.divider()
st.sidebar.caption("Protótipo acadêmico • Dados sintéticos")

# =========================================================
# VISÃO GERAL
# =========================================================

if pagina == "Visão Geral":
    st.markdown("""
    <div class="hero">
        <h1>Corporate Intelligence</h1>
        <p>
            Transformando informações corporativas em
            indicadores para apoiar decisões.
        </p>
    </div>
    """, unsafe_allow_html=True)

    total = len(clientes) + len(pessoas) + len(operacoes)
    negativos = (
        (clientes["sentimento"] == "Negativo").sum()
        + (pessoas["sentimento"] == "Negativo").sum()
    )
    pendentes = 0
    if "status" in operacoes.columns:
        pendentes = operacoes["status"].astype(str).str.lower().isin(
            ["aberto", "pendente", "em andamento", "em andamento "]
        ).sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total de registros", f"{total:,}".replace(",", "."))
    c2.metric("Feedbacks de clientes", len(clientes))
    c3.metric("Feedbacks de colaboradores", len(pessoas))
    c4.metric("Ocorrências operacionais", len(operacoes))

    st.divider()
    esquerda, direita = st.columns(2)

    with esquerda:
        st.subheader("Percepção de clientes")
        st.plotly_chart(
            grafico_sentimento(clientes, "Sentimento dos clientes"),
            use_container_width=True,
        )

    with direita:
        st.subheader("Clima organizacional")
        st.plotly_chart(
            grafico_sentimento(pessoas, "Sentimento dos colaboradores"),
            use_container_width=True,
        )

    esquerda, direita = st.columns(2)

    with esquerda:
        grafico_temporal(clientes, "data", "Evolução do feedback de clientes")

    with direita:
        grafico_temporal(
            operacoes, "data_abertura",
            "Evolução das ocorrências operacionais"
        )

    st.subheader("Visão operacional")
    o1, o2, o3 = st.columns(3)
    o1.metric("Ocorrências registradas", len(operacoes))
    o2.metric("Ocorrências pendentes", int(pendentes))
    o3.metric(
        "Feedbacks negativos identificados",
        int(negativos),
    )

    st.caption(
        "A classificação de sentimento é baseada em palavras-chave "
        "e serve apenas como demonstração inicial de análise textual."
    )

# =========================================================
# CLIENTES
# =========================================================

elif pagina == "Clientes":
    st.title("Experiência do Cliente")
    st.write(
        "Explore opiniões, canais de atendimento e temas recorrentes "
        "nos feedbacks recebidos."
    )

    f1, f2, f3 = st.columns(3)

    canal = f1.multiselect(
        "Canal",
        sorted(clientes["canal"].dropna().astype(str).unique())
        if "canal" in clientes.columns else [],
    )
    produto = f2.multiselect(
        "Produto ou serviço",
        sorted(clientes["produto_servico"].dropna().astype(str).unique())
        if "produto_servico" in clientes.columns else [],
    )
    sentimento = f3.multiselect(
        "Sentimento",
        ["Positivo", "Neutro", "Negativo"],
        default=["Positivo", "Neutro", "Negativo"],
    )

    filtrados = clientes.copy()
    filtrados = aplicar_filtro(filtrados, "canal", canal)
    filtrados = aplicar_filtro(filtrados, "produto_servico", produto)
    filtrados = aplicar_filtro(filtrados, "sentimento", sentimento)

    a, b, c = st.columns(3)
    a.metric("Feedbacks filtrados", len(filtrados))
    b.metric(
        "Positivos",
        int((filtrados["sentimento"] == "Positivo").sum()),
    )
    c.metric(
        "Negativos",
        int((filtrados["sentimento"] == "Negativo").sum()),
    )

    x, y = st.columns(2)
    with x:
        st.plotly_chart(
            grafico_sentimento(filtrados, "Distribuição de sentimentos"),
            use_container_width=True,
        )
    with y:
        grafico_barras(
            filtrados, "canal", "Feedbacks por canal de atendimento"
        )

    with st.expander("📋 Visualizar registros encontrados", expanded=False):
        st.caption(
            f"{len(filtrados)} registros encontrados com os filtros atuais."
        )
        mostrar_tabela(filtrados)

# =========================================================
# PESSOAS
# =========================================================

elif pagina == "Pessoas":
    st.title("Inteligência de Pessoas")
    st.write(
        "Analise percepções dos colaboradores sobre o ambiente de trabalho."
    )

    f1, f2, f3 = st.columns(3)

    departamento = f1.multiselect(
        "Departamento",
        sorted(pessoas["departamento"].dropna().astype(str).unique())
        if "departamento" in pessoas.columns else [],
    )
    categoria = f2.multiselect(
        "Categoria informada",
        sorted(
            pessoas["categoria_informada"].dropna().astype(str).unique()
        ) if "categoria_informada" in pessoas.columns else [],
    )
    sentimento = f3.multiselect(
        "Sentimento",
        ["Positivo", "Neutro", "Negativo"],
        default=["Positivo", "Neutro", "Negativo"],
    )

    filtrados = pessoas.copy()
    filtrados = aplicar_filtro(filtrados, "departamento", departamento)
    filtrados = aplicar_filtro(
        filtrados, "categoria_informada", categoria
    )
    filtrados = aplicar_filtro(filtrados, "sentimento", sentimento)

    a, b, c = st.columns(3)
    a.metric("Feedbacks filtrados", len(filtrados))
    b.metric(
        "Positivos",
        int((filtrados["sentimento"] == "Positivo").sum()),
    )
    c.metric(
        "Negativos",
        int((filtrados["sentimento"] == "Negativo").sum()),
    )

    x, y = st.columns(2)
    with x:
        st.plotly_chart(
            grafico_sentimento(
                filtrados, "Sentimento dos colaboradores"
            ),
            use_container_width=True,
        )
    with y:
        grafico_barras(
            filtrados, "departamento",
            "Feedbacks por departamento"
        )

    with st.expander("📋 Visualizar registros encontrados", expanded=False):
     st.caption(
        f"{len(filtrados)} registros encontrados com os filtros atuais."
     )
    mostrar_tabela(filtrados)

# =========================================================
# OPERAÇÕES
# =========================================================

elif pagina == "Operações":
    st.title("Eficiência Operacional")
    st.write(
        "Investigue ocorrências, prioridades, processos e situações "
        "que podem exigir atenção."
    )

    f1, f2, f3 = st.columns(3)

    departamento = f1.multiselect(
        "Departamento",
        sorted(operacoes["departamento"].dropna().astype(str).unique())
        if "departamento" in operacoes.columns else [],
    )
    prioridade = f2.multiselect(
        "Prioridade",
        sorted(operacoes["prioridade"].dropna().astype(str).unique())
        if "prioridade" in operacoes.columns else [],
    )
    status = f3.multiselect(
        "Status",
        sorted(operacoes["status"].dropna().astype(str).unique())
        if "status" in operacoes.columns else [],
    )

    filtrados = operacoes.copy()
    filtrados = aplicar_filtro(
        filtrados, "departamento", departamento
    )
    filtrados = aplicar_filtro(filtrados, "prioridade", prioridade)
    filtrados = aplicar_filtro(filtrados, "status", status)

    a, b, c = st.columns(3)
    a.metric("Ocorrências filtradas", len(filtrados))
    b.metric(
        "Prioridade alta",
        int(
            filtrados["prioridade"].astype(str).str.lower().isin(
                ["alta", "crítica", "critica", "urgente"]
            ).sum()
        ) if "prioridade" in filtrados.columns else 0,
    )
    c.metric(
        "Ocorrências não concluídas",
        int(
            filtrados["status"].astype(str).str.lower().isin(
                ["aberto", "pendente", "em andamento"]
            ).sum()
        ) if "status" in filtrados.columns else 0,
    )

    x, y = st.columns(2)
    with x:
        grafico_barras(
            filtrados, "prioridade",
            "Ocorrências por prioridade"
        )
    with y:
        grafico_barras(
            filtrados, "processo",
            "Processos com ocorrências"
        )

    grafico_temporal(
        filtrados, "data_abertura",
        "Ocorrências ao longo do tempo"
    )

    with st.expander("📋 Visualizar registros encontrados", expanded=False):
        st.caption(
            f"{len(filtrados)} registros encontrados com os filtros atuais."
        )
        mostrar_tabela(filtrados)

# =========================================================
# ASSISTENTE IA — PROTÓTIPO
# =========================================================

elif pagina == "Assistente IA":
    st.title("Assistente de Inteligência Corporativa")
    st.write(
        "Faça uma pergunta sobre os dados sintéticos para gerar "
        "um resumo demonstrativo."
    )

    st.info(
        "Este assistente ainda não utiliza um modelo de linguagem. "
        "As respostas abaixo são análises locais e demonstrativas."
    )

    pergunta = st.text_area(
        "Qual análise você deseja realizar?",
        placeholder=(
            "Ex.: Quais são os principais indicadores negativos? "
            "Quantas ocorrências existem? Como está a satisfação?"
        ),
    )

    if st.button("Analisar dados", type="primary"):
        if not pergunta.strip():
            st.warning("Digite uma pergunta para continuar.")
        else:
            texto_pergunta = pergunta.lower()

            total_neg_clientes = int(
                (clientes["sentimento"] == "Negativo").sum()
            )
            total_neg_pessoas = int(
                (pessoas["sentimento"] == "Negativo").sum()
            )

            if any(p in texto_pergunta for p in [
                "cliente", "satisfação", "satisfacao", "consumidor"
            ]):
                st.subheader("Análise de clientes")
                st.write(
                    f"Foram analisados **{len(clientes)} feedbacks** "
                    f"de clientes. A classificação preliminar identificou "
                    f"**{total_neg_clientes} feedbacks negativos**."
                )
                if "canal" in clientes.columns:
                    st.write("Canais com mais registros:")
                    st.dataframe(
                        clientes["canal"].value_counts().head(5)
                        .rename_axis("Canal")
                        .reset_index(name="Registros"),
                        hide_index=True,
                        use_container_width=True,
                    )

            elif any(p in texto_pergunta for p in [
                "colaborador", "funcionário", "funcionario",
                "equipe", "clima", "pessoas"
            ]):
                st.subheader("Análise de pessoas")
                st.write(
                    f"Foram analisados **{len(pessoas)} feedbacks** "
                    f"de colaboradores. A classificação preliminar "
                    f"identificou **{total_neg_pessoas} feedbacks "
                    f"negativos**."
                )
                if "departamento" in pessoas.columns:
                    st.write("Departamentos com mais registros:")
                    st.dataframe(
                        pessoas["departamento"].value_counts().head(5)
                        .rename_axis("Departamento")
                        .reset_index(name="Registros"),
                        hide_index=True,
                        use_container_width=True,
                    )

            elif any(p in texto_pergunta for p in [
                "operação", "operacao", "ocorrência", "ocorrencia",
                "processo", "prioridade", "falha"
            ]):
                st.subheader("Análise operacional")
                st.write(
                    f"A base contém **{len(operacoes)} ocorrências**."
                )
                if "status" in operacoes.columns:
                    st.write("Distribuição por status:")
                    st.dataframe(
                        operacoes["status"].value_counts()
                        .rename_axis("Status")
                        .reset_index(name="Registros"),
                        hide_index=True,
                        use_container_width=True,
                    )
                if "prioridade" in operacoes.columns:
                    st.write("Distribuição por prioridade:")
                    st.dataframe(
                        operacoes["prioridade"].value_counts()
                        .rename_axis("Prioridade")
                        .reset_index(name="Registros"),
                        hide_index=True,
                        use_container_width=True,
                    )

            else:
                st.subheader("Resumo geral")
                st.write(
                    f"A plataforma reúne **{len(clientes)} feedbacks "
                    f"de clientes**, **{len(pessoas)} feedbacks de "
                    f"colaboradores** e **{len(operacoes)} ocorrências "
                    f"operacionais**, totalizando "
                    f"**{len(clientes) + len(pessoas) + len(operacoes)} "
                    f"registros**."
                )
                st.write(
                    "Para uma análise mais específica, mencione "
                    "clientes, colaboradores, clima organizacional, "
                    "operações, processos ou prioridades."
                )

            st.caption(
                "Os resultados são exploratórios e não substituem "
                "a validação dos dados ou uma análise contextual."
            )
