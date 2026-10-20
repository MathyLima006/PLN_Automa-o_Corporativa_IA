
import os
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# Carrega as configurações do arquivo .env
load_dotenv()

URI = os.getenv("MONGODB_URI")

if not URI:
    raise ValueError("MONGODB_URI não encontrada no arquivo .env")

# Localiza a pasta data deste projeto
PASTA_PROJETO = Path(__file__).parent
PASTA_DADOS = PASTA_PROJETO / "data"

# Arquivos e coleções correspondentes
ARQUIVOS = {
    "clientes": "feedback_clientes.csv",
    "colaboradores": "feedback_colaboradores.csv",
    "operacoes": "ocorrencias_operacionais.csv",
}

cliente = MongoClient(URI, serverSelectionTimeoutMS=10000)
banco = cliente["corporate_intelligence"]

try:
    cliente.admin.command("ping")
    print("Conectado ao MongoDB Atlas!\n")

    for colecao_nome, arquivo_nome in ARQUIVOS.items():
        caminho = PASTA_DADOS / arquivo_nome

        if not caminho.exists():
            print(f"Arquivo não encontrado: {caminho}")
            continue

        # Lê o CSV e trata valores vazios como None
        df = pd.read_csv(caminho)
        df = df.astype(object).where(pd.notna(df), None)

        registros = df.to_dict(orient="records")
        colecao = banco[colecao_nome]

        # Substitui os registros da importação anterior
        # para evitar duplicações ao executar novamente.
        colecao.delete_many({})

        if registros:
            colecao.insert_many(registros)

        print(
            f"{colecao_nome}: "
            f"{colecao.count_documents({})} registros importados."
        )

    print("\nImportação concluída!")

except Exception as erro:
    print(f"Erro durante a importação: {erro}")

finally:
    cliente.close()
