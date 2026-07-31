import streamlit as st
import pandas as pd
import pdfplumber
import google.generativeai as genai
import json
import os

# 1. Configuração da Página
st.set_page_config(page_title="CotaMap | App Aberto", layout="wide", page_icon="🛒")

st.markdown("""
    <style>
    .metric-label { font-size: 11px; color: #666; text-transform: uppercase; font-weight: 600; }
    .metric-value { font-size: 20px; font-weight: bold; color: #1e3a8a; }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 CotaMap - Mapa de Cotação Inteligente")
st.markdown("**Sistema Aberto de Equalização de Compras**")
st.divider()

# 2. Resgate Seguro da Chave de API (Invisível para o usuário final)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.environ.get("GEMINI_API_KEY", "")

st.sidebar.header("⚙️ Configurações Fiscais")
icms_desc = st.sidebar.number_input("Desconto ICMS (%)", value=7.0, step=1.0)
pis_cofins = st.sidebar.number_input("Desconto PIS/COFINS (%)", value=9.25, step=0.01)

# 3. Área de Upload
st.subheader("1. Anexar Cotações")
st.info("Arraste os PDFs dos fornecedores. A Inteligência Artificial fará a leitura e o cruzamento dos itens.")
arquivos = st.file_uploader("Upload de Orçamentos (Apenas PDF)", type=["pdf"], accept_multiple_files=True)

if arquivos:
    if not api_key:
        st.error("⚠️ O administrador do sistema ainda não configurou a chave da IA no cofre do servidor.")
    else:
        if st.button("🤖 Processar PDFs e Gerar Mapa", type="primary"):
            with st.spinner("Lendo PDFs e cruzando itens com IA... Isso pode levar alguns segundos."):
                
                textos_cotacoes = ""
                for i, arquivo in enumerate(arquivos):
                    texto_pdf = f"\n--- INÍCIO DA COTAÇÃO {i+1} ({arquivo.name}) ---\n"
                    try:
                        with pdfplumber.open(arquivo) as pdf:
                            for pagina in pdf.pages:
                                extraido = pagina.extract_text()
                                if extraido:
                                    texto_pdf += extraido + "\n"
                        textos_cotacoes += texto_pdf
                    except Exception as e:
                        st.error(f"Erro ao ler o arquivo {arquivo.name}: {e}")
                
                genai.configure(api_key=api_key)
                
                prompt = f"""
                Você é um especialista em suprimentos e compras industriais. Analise os textos das cotações abaixo.
                Seu objetivo é padronizar os itens e criar um mapa comparativo. Cruze os itens que são iguais, mesmo que a descrição dos fornecedores mude um pouco.

                Retorne APENAS um JSON estrito, sem formatação markdown (sem ```json), neste formato exato:
                {{
                  "fornecedores": ["Nome Fornecedor A", "Nome Fornecedor B"],
                  "itens": [
                    {{
                      "descricao_padrao": "Nome do item padronizado",
                      "unidade": "UN",
                      "quantidade": 10,
                      "precos_unitarios": {{
                        "Nome Fornecedor A": 15.50,
                        "Nome Fornecedor B": 16.00
                      }}
                    }}
                  ]
                }}

                Cotações extraídas:
                {textos_cotacoes}
                """
                
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    resposta = model.generate_content(
                        prompt,
                        generation_config=genai.GenerationConfig(
                            response_mime_type="application/json",
                            temperature=0.1
                        )
                    )
                    
                    dados_json = json.loads(resposta.text)
                    
                    st.success("✅ Extração concluída com sucesso via IA!")
                    st.divider()
                    
                    st.subheader("2. Mapa de Cotação Estruturado")
                    
                    linhas = []
                    for item in dados_json.get("itens", []):
                        linha = {
                            "Item": item.get("descricao_padrao"),
                            "Unid.": item.get("unidade"),
                            "Qtd.": item.get("quantidade"),
                        }
                        for forn in dados_json.get("fornecedores", []):
                            preco_unit = item.get("precos_unitarios", {}).get(forn, 0.0)
                            linha[f"{forn} (Unit)"] = preco_unit
                            linha[f"{forn} (Total)"] = preco_unit * item.get("quantidade", 0)
                        
                        linhas.append(linha)
                    
                    df_mapa = pd.DataFrame(linhas)
                    
                    def pintar_fundo_colunas(x):
                        df_estilo = pd.DataFrame('', index=x.index, columns=x.columns)
                        cores = ['#e6f2ff', '#f3f4f6', '#fffbeb']
                        
                        fornecedores = dados_json.get("fornecedores", [])
                        for idx, forn in enumerate(fornecedores):
                            cor = cores[idx % len(cores)]
                            if f"{forn} (Unit)" in df_estilo.columns:
                                df_estilo[f"{forn} (Unit)"] = f'background-color: {cor}'
                                df_estilo[f"{forn} (Total)"] = f'background-color: {cor}'
                        return df_estilo
                    
                    st.dataframe(
                        df_mapa.style.apply(pintar_fundo_colunas, axis=None).format(precision=2),
                        use_container_width=True,
                        hide_index=True
                    )
                    
                except Exception as e:
                    st.error(f"Ocorreu um erro na comunicação com a IA ou no formato dos dados: {e}")
else:
    st.info("👆 Faça o upload de orçamentos em PDF para iniciar a análise automatizada.")
