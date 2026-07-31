import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="CotaMap | Parente Andrade", layout="wide", page_icon="🛒")

st.title("🛒 CotaMap - Mapa de Cotação Inteligente")
st.markdown("**Empresa:** Parente Andrade Ltda | **Regime:** Lucro Real | **Base:** Manaus (AM)")
st.divider()

# 2. Barra Lateral (Parâmetros Fiscais e Logísticos)
st.sidebar.header("⚙️ Configurações de Cálculo")
icms_desc = st.sidebar.number_input("Desconto ICMS - SUFRAMA (%)", value=7.0, step=1.0)
pis_cofins = st.sidebar.number_input("Desconto PIS/COFINS (%)", value=9.25, step=0.01)
frete_fob = st.sidebar.number_input("Estimativa Frete FOB (R$/Kg)", value=3.50, step=0.50)

# 3. Área de Upload (Simulação da IA)
st.subheader("1. Anexar Cotações")
st.info("Arraste os PDFs dos fornecedores abaixo. O sistema padronizará os itens para comparação.")
arquivos = st.file_uploader("Upload de Orçamentos (PDF, XLSX)", accept_multiple_files=True)

if arquivos:
    st.success(f"{len(arquivos)} arquivo(s) processado(s) com sucesso!")

# 4. Tabela Base (Valores Brutos)
st.subheader("2. Visão Bruta (Extraída dos Orçamentos)")
dados_simulados = {
    "Item / Descrição": ["Cabo Flexível 10mm", "Luminária LED 60W", "Capacete EPI"],
    "Qtd": [50, 100, 30],
    "Peso Unit (Kg)": [4.0, 1.5, 0.4],
    "Forn. A (SP) Bruto": [320.0, 85.0, 25.0],
    "Forn. A Frete": ["FOB", "FOB", "FOB"],
    "Forn. B (AM) Bruto": [300.0, 88.0, 28.0],
    "Forn. B Frete": ["CIF", "CIF", "CIF"],
}
df_bruto = pd.DataFrame(dados_simulados)
st.dataframe(df_bruto, use_container_width=True)

# 5. Motor de Cálculo (Custo Efetivo)
st.subheader("3. Mapa Comparativo: Custo Efetivo de Aquisição")
st.markdown("A tabela abaixo já deduz os impostos de fora do estado e **soma o custo de frete FOB**.")

def calcular_custo_efetivo(preco, peso, tipo_frete, fora_do_estado):
    custo_final = preco
    # Aplica desoneração para compras interestaduais (ZFM)
    if fora_do_estado:
        desconto_total = (icms_desc + pis_cofins) / 100
        custo_final = custo_final * (1 - desconto_total)
    
    # Adiciona custo de frete se for FOB
    if tipo_frete == "FOB":
        custo_final += (peso * frete_fob)
        
    return round(custo_final, 2)

# Gerando a tabela calculada
df_calc = pd.DataFrame()
df_calc["Item / Descrição"] = df_bruto["Item / Descrição"]
df_calc["Qtd"] = df_bruto["Qtd"]

df_calc["Efetivo A (SP)"] = df_bruto.apply(
    lambda x: calcular_custo_efetivo(x["Forn. A (SP) Bruto"], x["Peso Unit (Kg)"], x["Forn. A Frete"], True), axis=1
)
df_calc["Efetivo B (AM)"] = df_bruto.apply(
    lambda x: calcular_custo_efetivo(x["Forn. B (AM) Bruto"], x["Peso Unit (Kg)"], x["Forn. B Frete"], False), axis=1
)

# Destacando o menor preço em verde
def destacar_menor_preco(linha):
    is_min = linha == linha.min()
    return ['background-color: #198754; color: white; font-weight: bold' if v else '' for v in is_min]

tabela_formatada = df_calc.style.apply(
    destacar_menor_preco, subset=["Efetivo A (SP)", "Efetivo B (AM)"], axis=1
).format(precision=2)

st.dataframe(tabela_formatada, use_container_width=True)

# 6. Painel de Decisão
col1, col2 = st.columns(2)
total_sp = (df_calc["Efetivo A (SP)"] * df_calc["Qtd"]).sum()
total_am = (df_calc["Efetivo B (AM)"] * df_calc["Qtd"]).sum()

col1.metric("Total Fornecedor A (SP)", f"R$ {total_sp:,.2f}")
col2.metric("Total Fornecedor B (AM)", f"R$ {total_am:,.2f}")

st.button("✅ Exportar Mapa e Gerar Pedido", type="primary")
