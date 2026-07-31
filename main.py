import streamlit as st
import pandas as pd

# 1. Configuração da Página
st.set_page_config(page_title="CotaMap | Parente Andrade", layout="wide", page_icon="🛒")

st.markdown("""
    <style>
    .metric-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
    .metric-value { font-size: 20px; font-weight: bold; color: #1e3a8a; }
    .winner-box { background-color: #f0fdf4; border: 2px solid #22c55e; padding: 20px; border-radius: 10px; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 CotaMap - Equalização de Preços & Calculadora DIFAL / ST")
st.markdown("**Sistema de Suprimentos | Parente Andrade Ltda (Manaus - AM)**")
st.divider()

# 2. Parâmetros Fiscais e Logísticos Globais (Diretrizes Sefaz / Lei 6.108)
st.sidebar.header("⚙️ Parâmetros de Equalização Fiscal")
aliquota_destino = st.sidebar.number_input("Alíquota Interna Destino (AM %)", value=20.0, step=0.5) / 100.0
aliquota_origem = st.sidebar.number_input("Alíquota Interestadual Origem (%)", value=7.0, step=1.0) / 100.0
fcp_percentual = st.sidebar.number_input("Fundo de Combate à Pobreza (FCP %)", value=2.0, step=0.5) / 100.0

# 3. Entrada de Dados das Propostas Recebidas
st.subheader("1. Entrada de Propostas dos Fornecedores")
st.info("Insira os dados dos fornecedores e os valores totais propostos. O sistema executará a equalização intermunicipal (Frete FOB, ICMS ST e DIFAL) conforme o modelo da planilha.")

num_fornecedores = st.number_input("Quantidade de Fornecedores na Cotação", min_value=1, max_value=5, value=3, step=1)

fornecedores_dados = []

colunas_input = st.columns(int(num_fornecedores))

for i in range(int(num_fornecedores)):
    with colunas_input[i]:
        st.markdown(f"#### Fornecedor {i+1}")
        f_nome = st.text_input(f"Nome do Fornecedor", value=f"FORNECEDOR {i+1}", key=f"nome_{i}")
        f_origem = st.selectbox(f"Origem", ["Manaus - AM", "São Paulo - SP", "Outros Estados"], key=f"origem_{i}")
        f_bruto = st.number_input(f"Valor Total Bruto (R$)", value=10000.0 + (i * 2500.0), step=100.0, key=f"bruto_{i}")
        f_desc = st.number_input(f"Desconto (%)", value=0.0, step=1.0, key=f"desc_{i}") / 100.0
        
        is_local = ("Manaus" in f_origem or "AM" in f_origem)
        
        if is_local:
            st.success("Local (AM): Imposto 0")
            f_st = 0.0
            f_difal = 0.0
            f_frete = st.number_input(f"Frete Local (R$)", value=0.0, step=50.0, key=f"frete_{i}")
        else:
            st.warning("Interestadual: Aplica ST/DIFAL/FOB")
            f_st = st.number_input(f"ICMS ST (Fator/Ajuste)", value=0.7, step=0.1, key=f"st_{i}")
            
            base_difal = f_bruto * (1.0 - f_desc)
            difal_calc = base_difal * (aliquota_destino - aliquota_origem + fcp_percentual)
            f_difal = st.number_input(f"DIFAL (R$)", value=round(difal_calc, 2), step=50.0, key=f"difal_{i}")
            f_frete = st.number_input(f"Frete FOB (R$)", value=3200.0, step=100.0, key=f"frete_{i}")

        f_pagamento = st.text_input(f"Condição Pagamento", value="30 DDL", key=f"pag_{i}")
        f_entrega = st.text_input(f"Prazo de Entrega", value="15 Dias", key=f"ent_{i}")

        # Cálculo do Total Líquido e Total Geral
        total_liq = f_bruto * (1.0 - f_desc)
        total_geral = total_liq + f_frete + f_difal

        fornecedores_dados.append({
            "Fornecedor": f_nome.upper(),
            "Origem": f_origem,
            "Valor Total Bruto": f_bruto,
            "Desconto": f_bruto * f_desc,
            "Valor Líquido": total_liq,
            "ICMS ST / Ajuste": f_st,
            "DIFAL / Encargos": f_difal,
            "Frete": f_frete,
            "TOTAL GERAL": total_geral,
            "Cond. Pagamento": f_pagamento,
            "Prazo Entrega": f_entrega
        })

st.divider()
st.subheader("2. Mapa Comparativo Consolidado e Sugestão de Vencedor")

if st.button("📊 Gerar Mapa Comparativo e Apurar Vencedor", type="primary"):
    df_resumo = pd.DataFrame(fornecedores_dados)

    # Identifica o menor valor geral
    menor_valor = df_resumo["TOTAL GERAL"].min()
    vencedor_row = df_resumo[df_resumo["TOTAL GERAL"] == menor_valor].iloc[0]
    melhor_fornecedor = vencedor_row["Fornecedor"]

    st.dataframe(
        df_resumo.style.format({
            "Valor Total Bruto": "R$ {:,.2f}",
            "Desconto": "R$ {:,.2f}",
            "Valor Líquido": "R$ {:,.2f}",
            "ICMS ST / Ajuste": "{:,.2f}",
            "DIFAL / Encargos": "R$ {:,.2f}",
            "Frete": "R$ {:,.2f}",
            "TOTAL GERAL": "R$ {:,.2f}"
        }),
        width='stretch',
        hide_index=True
    )

    st.markdown(f"""
        <div class="winner-box">
            <h3>🏆 Sugestão de Fornecedor Vencedor: <b>{melhor_fornecedor}</b></h3>
            <p>Após a aplicação da equalização intermunicipal (somando frete, abatendo descontos e computando os encargos de DIFAL/ST conforme as diretrizes fiscais), o fornecedor com o <b>menor Custo Total Geral é {melhor_fornecedor} (R$ {menor_valor:,.2f})</b>.</p>
        </div>
    """, unsafe_allow_html=True)

    # Botões de Geração de OC
    st.markdown("<br>", unsafe_allow_html=True)
    cols_oc = st.columns(len(fornecedores_dados))
    for idx, row in df_resumo.iterrows():
        with cols_oc[idx]:
            st.metric(label=f"Total {row['Fornecedor']}", value=f"R$ {row['TOTAL GERAL']:,.2f}")
            st.button(f"Gerar OC - {row['Fornecedor']}", key=f"btn_oc_{idx}", use_container_width=True)
else:
    st.info("👆 Clique no botão acima para processar a matriz de equalização e gerar o mapa final.")
