import streamlit as st
import pandas as pd
import pdfplumber
from google import genai
import json
import os

# 1. Configuração da Página
st.set_page_config(page_title="CotaMap | Parente Andrade", layout="wide", page_icon="🛒")

st.markdown("""
    <style>
    .metric-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
    .metric-value { font-size: 20px; font-weight: bold; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 CotaMap - Mapa de Cotação Inteligente com IA")
st.markdown("**Sistema Aberto de Equalização de Compras | Parente Andrade Ltda (Manaus - AM)**")
st.divider()

# 2. Configurações Fiscais e Logísticas na Barra Lateral
st.sidebar.header("⚙️ Configurações Fiscais e Frete")
icms_desc = st.sidebar.number_input("Desconto ICMS - SUFRAMA (%)", value=7.0, step=1.0)
pis_cofins = st.sidebar.number_input("Desconto PIS/COFINS (%)", value=9.25, step=0.01)
frete_fob = st.sidebar.number_input("Estimativa Frete FOB (R$/Kg)", value=3.50, step=0.50)

# Resgate seguro da chave de IA oculta no servidor (Gratuita)
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
except:
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

# 3. Área de Upload Pública
st.subheader("1. Anexar Cotações dos Fornecedores")
st.info("Arraste os PDFs dos orçamentos. A Inteligência Artificial fará a leitura, cruzamento e equalização automática.")
arquivos = st.file_uploader("Upload de Orçamentos (PDF)", type=["pdf"], accept_multiple_files=True)

if arquivos:
    if not gemini_key:
        st.error("⚠️ Chave de IA do servidor não configurada. Adicione a GEMINI_API_KEY nos Secrets do Streamlit.")
    else:
        if st.button("🤖 Processar com Inteligência Artificial", type="primary"):
            with st.spinner("A IA está lendo os PDFs, cruzando os itens e calculando os custos efetivos..."):
                
                # Extraindo o texto de todos os PDFs anexados
                texto_completo_pdfs = ""
                for arquivo in arquivos:
                    texto_completo_pdfs += f"\n\n--- FORNECEDOR / ARQUIVO: {arquivo.name} ---\n"
                    try:
                        with pdfplumber.open(arquivo) as pdf:
                            for pagina in pdf.pages:
                                extraido = pagina.extract_text()
                                if extraido:
                                    texto_completo_pdfs += extraido + "\n"
                    except Exception as e:
                        st.error(f"Erro ao ler {arquivo.name}: {e}")

                # Prompt especializado para a IA estruturar a cotação
                prompt = f"""
                Você é um analista sênior de suprimentos e compras industriais. 
                Analise os textos extraídos dos PDFs de cotação de diferentes fornecedores abaixo.
                Seu trabalho é:
                1. Identificar o nome de cada fornecedor.
                2. Padronizar os itens equivalentes entre os orçamentos (mesmo que a descrição varie ligeiramente).
                3. Extrair a quantidade cotada, a unidade e o preço unitário cobrado por cada fornecedor para cada item.

                Retorne APENAS um objeto JSON válido, sem formatação markdown (sem ```json), exatamente neste formato:
                {{
                  "fornecedores": ["Nome do Fornecedor 1", "Nome do Fornecedor 2"],
                  "itens": [
                    {{
                      "descricao": "Nome padronizado do item",
                      "unidade": "UN",
                      "quantidade": 10.0,
                      "peso_unitario_kg": 1.5,
                      "precos_unitarios": {{
                        "Nome do Fornecedor 1": 150.00,
                        "Nome do Fornecedor 2": 145.50
                      }}
                    }}
                  ]
                }}

                Textos das cotações:
                {texto_completo_pdfs}
                """

                try:
                    # Chamada oficial e gratuita ao Gemini Flash
                    client = genai.Client(api_key=gemini_key)
                    resposta = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    # Tratamento da resposta da IA
                    texto_resposta = resposta.text.replace("```json", "").replace("```", "").strip()
                    dados_json = json.loads(texto_resposta)
                    
                    fornecedores = dados_json.get("fornecedores", [])
                    itens_IA = dados_json.get("itens", [])

                    # Montando a tabela estruturada com base na inteligência da IA
                    tabela_dados = {
                        "Item": [item["descricao"] for item in itens_IA],
                        "Unid.": [item["unidade"] for item in itens_IA],
                        "Qtd.": [item["quantidade"] for item in itens_IA],
                    }

                    fator_impostos = 1.0 - ((icms_desc + pis_cofins) / 100.0)

                    # Preenchendo os valores por fornecedor com aplicação de impostos e frete FOB
                    for idx, forn in enumerate(fornecedores):
                        precos_efetivos = []
                        totais_efetivos = []
                        
                        # Considera fornecedor 0 de fora do estado (com imposto/frete) e demais locais (ou ajustável)
                        fora_do_estado = (idx == 0) 

                        for item in itens_IA:
                            p_base = item.get("precos_unitarios", {}).get(forn, 0.0)
                            peso = item.get("peso_unitario_kg", 0.5)
                            q = item.get("quantidade", 1.0)
                            
                            custo = p_base
                            if fora_do_estado:
                                custo = custo * fator_impostos  # Desconto SUFRAMA + PIS/COFINS
                                custo += (peso * frete_fob)     # Adiciona Frete FOB
                            
                            precos_efetivos.append(round(custo, 2))
                            totais_efetivos.append(round(custo * q, 2))

                        tabela_dados[f"{forn} (Unit. Efetivo)"] = precos_efetivos
                        tabela_dados[f"{forn} (Total)"] = totais_efetivos

                    df_mapa = pd.DataFrame(tabela_dados)

                    st.success("✅ Análise e cruzamento de itens realizados com sucesso via IA!")
                    st.divider()
                    
                    st.subheader("2. Mapa Comparativo de Custo Efetivo")
                    st.markdown("*Custos equalizados com base na legislação fiscal de Manaus (ICMS/PIS/COFINS e Frete FOB).*")

                    def destacar_colunas(x):
                        df_estilo = pd.DataFrame('', index=x.index, columns=x.columns)
                        cores = ['#e6f2ff', '#f3f4f6', '#fffbeb']
                        for idx, forn in enumerate(fornecedores):
                            cor = cores[idx % len(cores)]
                            col_unit = f"{forn} (Unit. Efetivo)"
                            col_tot = f"{forn} (Total)"
                            if col_unit in df_estilo.columns:
                                df_estilo[col_unit] = f'background-color: {cor}'
                                df_estilo[col_tot] = f'background-color: {cor}'
                        return df_estilo

                    st.dataframe(
                        df_mapa.style.apply(destacar_colunas, axis=None).format(precision=2),
                        width='stretch',
                        hide_index=True
                    )

                    # Painel de Fechamento e Pedidos
                    st.markdown("<br>", unsafe_allow_inner=True if hasattr(st, 'markdown') else False)
                    cols = st.columns(len(fornecedores) if len(fornecedores) > 0 else 1)
                    
                    for idx, forn in enumerate(fornecedores):
                        coluna_total = f"{forn} (Total)"
                        if coluna_total in df_mapa.columns:
                            total_fornecedor = df_mapa[coluna_total].sum()
                            with cols[idx]:
                                st.metric(label=f"Custo Efetivo {forn}", value=f"R$ {total_fornecedor:,.2f}")
                                st.button(f"Gerar OC - {forn}", key=f"btn_ia_{idx}", use_container_width=True)

                except Exception as e:
                    st.error(f"Erro ao processar os dados com a IA: {e}")
else:
    st.info("👆 Faça o upload dos PDFs dos fornecedores para a IA iniciar a equalização automática.")
