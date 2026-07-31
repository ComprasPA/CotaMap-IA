import streamlit as st
import pandas as pd
from datetime import date

# 1. Configuração da Página
st.set_page_config(page_title="CotaMap | Parente Andrade", layout="wide", page_icon="🛒")

# Customização CSS para deixar com cara de ERP
st.markdown("""
    <style>
    .metric-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
    .metric-value { font-size: 20px; font-weight: bold; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

# 2. Área de Upload / Controle de Exibição
col_up1, col_up2 = st.columns([3, 1])
with col_up1:
    arquivos = st.file_uploader("Anexar Orçamentos (PDF, XLSX)", accept_multiple_files=True)
with col_up2:
    st.markdown("<br>", unsafe_allow_html=True)
    modo_teste = st.toggle("Ativar Layout de Teste (Visualizar Painel)")

if arquivos or modo_teste:
    
    st.divider()

    # 3. Cabeçalho Resumo (Inspirado no ERP)
    c1, c2, c3, c4, c5, c6 = st.columns([1, 1, 1.5, 1.5, 1.5, 2])
    with c1:
        st.markdown("<div class='metric-label'>Compras</div><div class='metric-value'>Cotação</div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='metric-label'>Itens</div><div class='metric-value'>4</div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='metric-label'>Fornecedores</div><div class='metric-value'>2</div>", unsafe_allow_html=True)
    with c4:
        st.markdown("<div class='metric-label'>Criação</div><div class='metric-value' style='font-size:16px; margin-top:4px;'>29/11/2026</div>", unsafe_allow_html=True)
    with c5:
        st.markdown("<div class='metric-label'>Comprador</div><div class='metric-value' style='font-size:16px; margin-top:4px;'>Sílvio Vasconcelos</div>", unsafe_allow_html=True)
    with c6:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("✔️ Salvar Cotação", type="primary", use_container_width=True)

    st.markdown("<hr style='margin: 10px 0; opacity: 0.3;'>", unsafe_allow_html=True)

    # 4. Linha de Filtros e Parâmetros
    f1, f2, f3, f4, f5, f6 = st.columns(6)
    f1.text_input("Número:", value="1")
    f2.selectbox("Status:", ["Finalizado", "Em cotação", "Aguardando Aprovação"])
    f3.selectbox("Prioridade:", ["Não", "Sim - Urgente"])
    f4.date_input("Necessidade:", value=date.today())
    f5.selectbox("Solicitante:", ["Selecione", "Engenharia", "Almoxarifado"])
    with f6:
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("🖨️ Imprimir Mapa", use_container_width=True)

    # 5. Abas de Navegação
    tab_itens, tab_forn, tab_mapa = st.tabs(["Itens", "Fornecedores", "Mapa de Cotação"])

    with tab_mapa:
        # Dados idênticos aos da imagem de referência
        dados = {
            "Item": ["Aço ca-50, 8.0 mm, vergalhão", "Areia média", "Cimento portland composto cp ii-32", "Pedra britada n. 1 (9,5 a 19 mm)"],
            "Unid.": ["Kg", "M³", "50 Kg", "M³"],
            "Qtd. Cotada": [30.00, 5.00, 10.00, 3.00],
            "Fornecedor 1 (Unit)": [5.30, 90.00, 18.00, 10.00],
            "Fornecedor 1 (Total)": [159.00, 450.00, 180.00, 30.00],
            "Fornecedor 2 (Unit)": [5.50, 88.00, 18.00, 12.00],
            "Fornecedor 2 (Total)": [165.00, 440.00, 180.00, 36.00],
            "Melhor Compra (Unit)": [5.30, 88.00, 18.00, 10.00],
            "Melhor Compra (Total)": [159.00, 440.00, 180.00, 30.00]
        }
        df = pd.DataFrame(dados)

        # Estilização das colunas para replicar o fundo azul/cinza do ERP
        def aplicar_cores(x):
            cor_f1 = 'background-color: #e6f2ff' # Azul clarinho
            cor_f2 = 'background-color: #f3f4f6' # Cinza clarinho
            cor_melhor = 'background-color: #ffffff; font-weight: bold; color: #047857' # Branco com verde
            
            df_estilo = pd.DataFrame('', index=x.index, columns=x.columns)
            df_estilo['Fornecedor 1 (Unit)'] = cor_f1
            df_estilo['Fornecedor 1 (Total)'] = cor_f1
            df_estilo['Fornecedor 2 (Unit)'] = cor_f2
            df_estilo['Fornecedor 2 (Total)'] = cor_f2
            df_estilo['Melhor Compra (Unit)'] = cor_melhor
            df_estilo['Melhor Compra (Total)'] = cor_melhor
            return df_estilo

        # Renderização da Tabela
        st.dataframe(
            df.style.apply(aplicar_cores, axis=None).format(precision=2),
            use_container_width=True,
            hide_index=True
        )

        # 6. Rodapé de Totais e Decisão (Botões "Gerar OC")
        st.markdown("<br>", unsafe_allow_html=True)
        t1, t2, t3, t4 = st.columns([3, 2, 2, 2])
        
        with t1:
            st.info("📊 **Resumo de Subtotais do Mapa**")
            st.write("Selecione os vencedores ao lado para gerar as Ordens de Compra no ERP.")
            
        with t2:
            st.success("🏆 **Fornecedor 1**\n\nTotal: **R$ 819,00**")
            st.button("Gerar OC - Forn. 1", use_container_width=True)
            
        with t3:
            st.warning("⚪ **Fornecedor 2**\n\nTotal: **R$ 821,00**")
            st.button("Gerar OC - Forn. 2", use_container_width=True)
            
        with t4:
            st.error("💡 **Melhor Combinação**\n\nTotal: **R$ 809,00**")
            st.markdown("*Economia de R$ 10,00*")

else:
    # Tela limpa inicial
    st.info("👆 O painel de equalização está oculto. Faça o upload dos orçamentos acima ou ative o 'Modo de Teste' para visualizar a interface.")
