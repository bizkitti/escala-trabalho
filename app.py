from flask import Flask, render_template, redirect, url_for, request
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)

# -----------------------------
# 1. Ler e preparar a tabela
# -----------------------------
def carregar_escala():
    df = pd.read_excel("escala.xlsx")

    # Converter Data
    if pd.api.types.is_numeric_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"], unit="d", origin="1899-12-30")
    else:
        df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce")

    # Criar colunas ISO reais
    df["ISO_Ano"] = df["Data"].apply(lambda d: d.isocalendar().year)
    df["ISO_Semana"] = df["Data"].apply(lambda d: d.isocalendar().week)

    # Semana ISO com zero à esquerda (ESSENCIAL para ordenar corretamente)
    df["SemanaISO"] = df["ISO_Ano"].astype(str) + "-" + df["ISO_Semana"].astype(str).str.zfill(2)

    # Dia da semana (Seg=0 ... Dom=6)
    df["DiaNum"] = df["Data"].dt.weekday

    # Ordenação correta
    df = df.sort_values(by=["ISO_Ano", "ISO_Semana", "Colaborador", "Data"])

    return df


# -----------------------------
# 2. Normalização dos horários
# -----------------------------
def normalizar(h):
    if pd.isna(h):
        return ""
    h = str(h).lower()
    h = h.replace(" ", "")
    h = h.replace("\u200b", "")
    h = h.replace("\u00a0", "")
    return h


# -----------------------------
# 3. Mapeamento de cores
# -----------------------------
def classe_cor_por_horario(horario):
    h = normalizar(horario)

    mapa = {
        "5h-14h": "cor-5h-14h",
        "7:30h-16:30h": "cor-730h-1630h",
        "8:30h-17:30h": "cor-830h-1730h",
        "9h-18h": "cor-9h-18h",
        "10h-19h": "cor-10h-19h",
        "6h-15h": "cor-6h-15h",
        "folga": "cor-Folga",
        "férias": "cor-Férias"
    }

    return mapa.get(h, "")


# -----------------------------
# 4. Datas da semana ISO
# -----------------------------
def datas_da_semana(semana_iso):
    ano_iso, semana = semana_iso.split("-")
    ano_iso = int(ano_iso)
    semana = int(semana)

    inicio = datetime.fromisocalendar(ano_iso, semana, 1)
    return [(inicio + timedelta(days=i)).strftime("%d/%m") for i in range(7)]


# -----------------------------
# 5. Gerar matriz semanal
# -----------------------------
def gerar_matriz_semana(df, semana_iso, colaborador=None):
    dados = df[df["SemanaISO"] == semana_iso].copy()

    if colaborador and colaborador != "Todos":
        dados = dados[dados["Colaborador"] == colaborador]

    dados["Grupo"] = pd.to_numeric(dados["Grupo"], errors="coerce").fillna(99)
    ordem = dados.groupby("Colaborador")["Grupo"].min().sort_values()
    colaboradores = ordem.index.tolist()

    matriz = []

    for colab in colaboradores:
        linha = {"colaborador": colab, "dias": []}

        for dia_num in range(7):
            celula = dados[(dados["Colaborador"] == colab) & (dados["DiaNum"] == dia_num)]

            if celula.empty:
                linha["dias"].append({
                    "regime": "",
                    "horario": "",
                    "grupo": "",
                    "data": "",
                    "classe_cor": ""
                })
            else:
                item = celula.sort_values(by="Data").iloc[-1]

                regime = str(item["Regime"])
                horario = str(item["Horário"])
                grupo = str(item["Grupo"])
                data_str = item["Data"].strftime("%Y-%m-%d")

                chave_cor = horario if regime.lower() not in ["folga", "férias"] else regime

                linha["dias"].append({
                    "regime": regime,
                    "horario": horario,
                    "grupo": grupo,
                    "data": data_str,
                    "classe_cor": classe_cor_por_horario(chave_cor)
                })

        matriz.append(linha)

    return matriz


# -----------------------------
# 6. Rotas
# -----------------------------
@app.route("/")
def index():
    return redirect("/hoje")


@app.route("/hoje")
def hoje():
    ano = datetime.now().isocalendar().year
    semana = datetime.now().isocalendar().week
    semana_iso = f"{ano}-{str(semana).zfill(2)}"
    return redirect(url_for("ver_semana", semana_iso=semana_iso))


@app.route("/semana/<semana_iso>", methods=["GET", "POST"])
def ver_semana(semana_iso):
    df = carregar_escala()  # Recarrega sempre
    colaborador = request.form.get("colaborador", "Todos")

    semanas = sorted(df["SemanaISO"].unique())

    if semana_iso not in semanas:
        semana_iso = semanas[0]

    idx = semanas.index(semana_iso)
    semana_anterior = semanas[idx - 1] if idx > 0 else None
    semana_seguinte = semanas[idx + 1] if idx < len(semanas) - 1 else None

    matriz = gerar_matriz_semana(df, semana_iso, colaborador)
    datas = datas_da_semana(semana_iso)
    lista_colaboradores = sorted(df["Colaborador"].unique())

    return render_template(
        "semana.html",
        semana=semana_iso,
        semanas=semanas,
        matriz=matriz,
        datas=datas,
        semana_anterior=semana_anterior,
        semana_seguinte=semana_seguinte,
        colaboradores=lista_colaboradores,
        colaborador_selecionado=colaborador
    )


# -----------------------------
# 7. Página do colaborador
# -----------------------------
@app.route("/colaborador/<nome>")
def pagina_colaborador(nome):
    df = carregar_escala()  # Recarrega sempre

    dados = df[df["Colaborador"] == nome].copy()

    if dados.empty:
        return f"Colaborador '{nome}' não encontrado."

    semanas = sorted(dados["SemanaISO"].unique())

    historico = []
    for semana in semanas:
        semana_dados = dados[dados["SemanaISO"] == semana]

        dias = []
        for _, row in semana_dados.iterrows():
            dias.append({
                "data": row["Data"].strftime("%d/%m/%Y"),
                "regime": row["Regime"],
                "horario": row["Horário"],
                "classe_cor": classe_cor_por_horario(
                    row["Horário"] if str(row["Regime"]).lower() not in ["folga", "férias"] else row["Regime"]
                )
            })

        historico.append({
            "semana": semana,
            "dias": dias
        })

    total_folgas = sum(dados["Regime"].str.lower() == "folga")
    total_ferias = sum(dados["Regime"].str.lower() == "férias")
    total_trabalhados = len(dados) - total_folgas - total_ferias

    return render_template(
        "colaborador.html",
        nome=nome,
        historico=historico,
        total_folgas=total_folgas,
        total_ferias=total_ferias,
        total_trabalhados=total_trabalhados
    )


# -----------------------------
# 8. Execução
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
