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

st.title("🛒 CotaMap - Sistema de Equalização de Preços & Calculadora DIFAL/ST")
st.markdown("**Departamento de Suprimentos | Parente Andrade Ltda (Manaus - AM)**")
st.divider()

# 2. Parâmetros Fiscais (Diretrizes SEFAZ-AM / Lei 6.108/2022)
st.sidebar.header("⚙️ Parâmetros Fiscais e Tributários")
aliquota_destino = st.sidebar.number_input("Alíquota Interna AM (%)", value=20.0, step=0.5) / 100.0
aliquota_origem = st.sidebar.number_input("Alíquota Interestadual (%)", value=7.0, step=1.0) / 100.0
fcp_aliq = st.sidebar.number_input("Fundo de Combate à Pobreza - FCP (%)", value=2.0, step=0.5) / 100.0

# 3. Entrada de Propostas Comercial / Itens da Cotação
st.subheader("1. Matriz de Propostas e Equalização Intermunicipal")
st.info("Insira os dados da cotação (baseado no modelo da sua planilha de equalização). O motor calcula automaticamente os líquidos, ST, DIFAL, frete e apura o menor custo.")

# Configuração de Itens da Cotação
num_itens = st.number_input("Quantidade de Itens na Cotação", min_value=1, max_value=10, value=1, step=1)

itens_proposta = []
for i in range(int(num_itens)):
    cols_it = st.columns([3, 1, 1])
    with cols_it[0]:
        desc_item = st.text_input(f"Descrição do Item {i+1}", value="BALANÇA 1000KGS", key=f"desc_{i}")
    with cols_it[1]:
        qtd_item = st.number_input(f"Qtde {i+1}", value=1.0, step=1.0, key=f"qtd_{i}")
    with cols_it[2]:
        un_item = st.text_input(f"Unid {i+1}", value="UN", key=f"un_{i}")
    itens_proposta.append({"descricao": desc_item, "qtd": qtd_item, "un": un_item})

st.divider()
st.subheader("2. Valores por Fornecedor (Propostas Brutas)")

num_fornecedores = st.number_input("Quantidade de Fornecedores", min_value=1, max_value=5, value=3, step=1)
fornecedores_data = []
cols_forn = st.columns(int(num_fornecedores))

for f in range(int(num_fornecedores)):
    with cols_forn[f]:
        st.markdown(f"#### Fornecedor {f+1}")
        f_nome = st.text_input(f"Nome Fornecedor {f+1}", value=f"FORNECEDOR {f+1}", key=f"fnome_{f}")
        f_origem = st.selectbox(f"Origem {f+1}", ["Manaus - AM", "São Paulo - SP", "Outros Estados"], key=f"forig_{f}")
        
        # Preço total bruto somado dos itens
        f_bruto = st.number_input(f"Valor Total Bruto (R$) - {f_nome}", value=10000.0 + (f * 3500.0), step=100.0, key=f"fbruto_{f}")
        f_desc_perc = st.number_input(f"Desconto (%) - {f_nome}", value=0.0, step=1.0, key=f"fdesc_{f}") / 100.0
        
        is_local = ("Manaus" in f_origem or "AM" in f_origem)
        
        if is_local:
            st.success("Fornecedor Local (AM): Imposto 0 / Isento de DIFAL e ST Interestadual")
            st_val = 0.0
            difal_val = 0.0
            frete_val = st.number_input(f"Frete Local (R$) - {f_nome}", value=0.0, step=100.0, key=f"ffrete_{f}")
        else:
            st.warning("Interestadual: Incide DIFAL, ST e Frete FOB")
            st_val = st.number_input(f"ICMS ST (Ajuste) - {f_nome}", value=0.7, step=0.1, key=f"fst_{f}")
            
            # Cálculo exato de DIFAL conforme a calculadora da planilha (Base * Alíquotas SEFAZ)
            base_calculo = f_bruto * (1.0 - f_desc_perc)
            difal_calculado = base_calculo * (aliquota_destino - aliquota_origem + fcp_percentual)
            difal_val = st.number_input(f"DIFAL (R$) - {f_nome}", value=round(difal_calculado, 2), step=100.0, key=f"fdifal_{f}")
            frete_val = st.number_input(f"Frete FOB (R$) - {f_nome}", value=3200.0, step=100.0, key=f"ffrete_{f}")

        f_pagamento = st.text_input(f"Cond. Pagamento - {f_nome}", value="30 DDL", key=f"fpag_{f}")
        f_entrega = st.text_input(f"Prazo Entrega - {f_nome}", value="15 Dias úteis", key=f"fent_{f}")

        # Matemática de fechamento idêntica à planilha de equalização
        val_liquido = f_bruto * (1.0 - f_desc_perc)
        total_geral_forn = val_liquido + frete_val + difal_val

        fornecedores_data.append({
            "Fornecedor": f_nome.upper(),
            "Origem": f_origem,
            "Valor Total Bruto": f_bruto,
            "Desconto": f_bruto * f_desc_perc,
            "Valor Líquido": val_liquido,
            "ICMS ST / Ajuste": st_val,
            "DIFAL / Encargos": difal_val,
            "Frete": frete_val,
            "TOTAL GERAL": total_geral_forn,
            "Cond. Pagamento": f_pagamento,
            "Prazo Entrega": f_entrega
        })

st.divider()
st.subheader("3. Mapa Comparativo Consolidado e Apuração de Vencedor")

if st.button("📊 Gerar Mapa Comparativo Final", type="primary"):
    df_resultado = pd.DataFrame(fornecedores_data)

    # Identifica o menor valor total geral
    menor_custo = df_resultado["TOTAL GERAL"].min()
    vencedor_Row = df_resultado[df_resultado["TOTAL GERAL"] == menor_custo].iloc[0]
    melhor_forn = vencedor_Row["Fornecedor"]

    st.dataframe(
        df_resultado.style.format({
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

    # Destaque do Vencedor
    st.markdown(f"""
        <div class="winner-box">
            <h3>🏆 Sugestão de Fornecedor Vencedor: <b>{melhor_forn}</b></h3>
            <p>Após a equalização intermunicipal rigorosa (abatendo descontos, computando o frete e somando os encargos de DIFAL/ST para operações interestaduais conforme as normas da SEFAZ-AM), o fornecedor com o <b>menor Custo Total Geral é {melhor_forn} (R$ {menor_custo:,.2f})</b>.</p>
        </div>
    """, unsafe_allow_html=True)

    # Botões de Ordem de Compra (OC)
    st.markdown("<br>", unsafe_allow_html=True)
    cols_oc = st.columns(len(fornecedores_data))
    for idx, row in df_resultado.iterrows():
        with cols_oc[idx]:
            st.metric(label=f"Total {row['Fornecedor']}", value=f"R$ {row['TOTAL GERAL']:,.2f}")
            st.button(f"Gerar OC - {row['Fornecedor']}", key=f"btn_oc_{idx}", use_container_width=True)
else:
    st.info("👆 Clique no botão acima para consolidar a matriz e gerar o comparativo final.")
