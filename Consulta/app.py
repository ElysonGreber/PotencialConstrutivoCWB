from flask import Flask, request, render_template
import requests
import pandas as pd

app = Flask(__name__)

# Parâmetros de zoneamento
zoneamento_data = [
    ["ZR1", 1.5, 0.50, 0.30, 3, "5 m", "360 m²", "12 m"],
    ["ZR2", 1.0, 0.50, 0.30, 2, "5 m", "360 m²", "12 m"],
    ["ZR3", 1.0, 0.50, 0.30, 2, "5 m", "360 m²", "12 m"],
    ["ZR4", 1.0, 0.50, 0.30, 2, "5 m", "360 m²", "12 m"],
    ["ZR5", 1.0, 0.50, 0.30, 2, "5 m", "360 m²", "12 m"],
    ["ZUM", 2.0, 0.70, 0.20, 6, "5 m", "300 m²", "12 m"],
    ["ZC", 3.0, 0.80, 0.15, 8, "5 m", "300 m²", "12 m"],
    ["ZPI", 2.5, 0.60, 0.25, 6, "10 m", "1.000 m²", "20 m"],
    ["ZOE", 1.0, 0.50, 0.30, 3, "5 m", "500 m²", "15 m"],
    ["ZPDS", 0.5, 0.20, 0.50, 2, "10 m", "2.000 m²", "30 m"]
]

zoneamento_df = pd.DataFrame(zoneamento_data, columns=[
    "Zona", "Coeficiente_Aproveitamento", "Taxa_Ocupacao", "Taxa_Perm",
    "Altura_Max_Pav", "Recuo_Min", "Area_Min_Lote", "Testada_Min"
])

# Consulta camada 15
def get_lote_info(indicacao_fiscal):
    url = "https://geocuritiba.ippuc.org.br/server/rest/services/GeoCuritiba/Publico_GeoCuritiba_MapaCadastral/MapServer/15/query"
    params = {
        "where": f"gtm_ind_fiscal = '{indicacao_fiscal}'",
        "outFields": "*",
        "f": "json"
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data and "features" in data and data["features"]:
            return data["features"][0]["attributes"]
    except:
        pass
    return None

# Consulta camada 20 (múltiplos registros)
def get_lote_info_extra(indicacao_fiscal):
    url = "https://geocuritiba.ippuc.org.br/server/rest/services/GeoCuritiba/Publico_GeoCuritiba_MapaCadastral/MapServer/20/query"
    params = {
        "where": f"gtm_ind_fiscal = '{indicacao_fiscal}'",
        "outFields": "*",
        "f": "json"
    }
    try:
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data and "features" in data:
            return [f["attributes"] for f in data["features"]]
    except:
        pass
    return []

@app.route("/", methods=["GET", "POST"])
def index():
    tabela = None
    mensagem = None

    if request.method == "POST":
        indicacao_fiscal = request.form.get("indicacao_fiscal")
        lote_info = get_lote_info(indicacao_fiscal)
        lote_extra = get_lote_info_extra(indicacao_fiscal)

        html_calc = ""
        html_lote = ""
        html_extra = ""

        if lote_info:
            zona = lote_info.get("gtm_sigla_zoneamento", "").strip()
            area_terreno = lote_info.get("gtm_mtr_area_terreno", 0)
            df_lote = pd.DataFrame(lote_info.items(), columns=["Campo", "Valor"])
            html_lote = df_lote.to_html(classes="table table-sm table-bordered", index=False, border=0)

            parametros = zoneamento_df[zoneamento_df["Zona"] == zona]

            if not parametros.empty and area_terreno:
                coef = parametros.iloc[0]["Coeficiente_Aproveitamento"]
                taxa_ocup = parametros.iloc[0]["Taxa_Ocupacao"]
                taxa_perm = parametros.iloc[0]["Taxa_Perm"]
                altura_max = parametros.iloc[0]["Altura_Max_Pav"]
                recuo_min = parametros.iloc[0]["Recuo_Min"]
                area_min_lote = parametros.iloc[0]["Area_Min_Lote"]
                testada_min = parametros.iloc[0]["Testada_Min"]

                area_max_construida = area_terreno * coef
                area_max_ocupada = area_terreno * taxa_ocup
                area_min_permeavel = area_terreno * taxa_perm

                calculos = {
                    "Zona": zona,
                    "Área do Lote (m²)": f"{area_terreno:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " m²",
                    "Coef. de Aproveitamento": coef,
                    "Taxa de Ocupação": f"{taxa_ocup * 100:.0f}%",
                    "Taxa de Permeabilidade": f"{taxa_perm * 100:.0f}%",
                    "Altura Máxima (Pavimentos)": f"{altura_max} pavimentos",
                    "Área Máx. Construída (m²)": f"{area_max_construida:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " m²",
                    "Área Máx. Ocupada (m²)": f"{area_max_ocupada:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " m²",
                    "Área Mín. Permeável (m²)": f"{area_min_permeavel:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " m²",
                    "Recuo Mínimo": recuo_min,
                    "Área Mínima do Lote": area_min_lote,
                    "Testada Mínima": testada_min
                }

                df_calc = pd.DataFrame(calculos.items(), columns=["Cálculo", "Valor"])
                html_calc = df_calc.to_html(classes="table table-sm table-bordered", index=False, border=0)
            else:
                html_lote += f"<div class='alert alert-warning'>Zona '{zona}' não reconhecida ou área inválida.</div>"
        else:
            mensagem = "Nenhuma informação encontrada na Camada 15 para a indicação fiscal fornecida."

        # Camada 20: múltiplos registros
        if lote_extra:
            html_extra = "<h4>Dados Complementares (Camada 20)</h4>"
            for i, item in enumerate(lote_extra, start=1):
                df = pd.DataFrame(item.items(), columns=["Campo", "Valor"])
                html_extra += f"<h5>Registro {i}</h5>" + df.to_html(classes="table table-sm table-bordered", index=False, border=0)

        # Montagem final na ordem desejada
        tabela = ""
        if html_calc:
            tabela += "<h4>Cálculo de Potencial Construtivo</h4>" + html_calc
        if html_lote:
            tabela += "<h4>Dados do Lote (Camada 15)</h4>" + html_lote
        if html_extra:
            tabela += html_extra

    return render_template("index.html", tabela=tabela, mensagem=mensagem)

if __name__ == "__main__":
    app.run(debug=True)
