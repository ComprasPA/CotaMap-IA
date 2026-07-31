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
    .winner-box { background-color: #f0fdf4; border: 2px solid #22c55e; padding: 20px; border-radius: 10px; margin-top: 20px; }
    </style>
""", unsafe_allow_html=True)

st.title("🛒 CotaMap - Mapa de Cotação Inteligente com IA & Equalización Fiscal")
st.markdown("**Sistema de Suprimentos | Parente Andrade Ltda (Manaus - AM)**")
st.divider()

# 2. Configurações Fiscais e Logísticas na Barra Lateral
st.sidebar.header("⚙️ Parâmetros Fiscais e Frete")
icms_suframa = st.sidebar.number_input("Desconto ICMS - SUFRAMA (%)", value=7.0, step=1.0)
pis_cofins = st.sidebar.number_input("Desconto PIS/COFINS (%)", value=9.25, step=0.01)
frete_fob_kg = st.sidebar.number_input("Média Frete FOB (R$/Kg)", value=3.50, step=0.50)
aliquota_interna_am = st.sidebar.number_input("Alíquota Interna AM (ICMS %)", value=18.0, step=1.0)

# Resgate seguro da chave de IA oculta no servidor
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
except:
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

# 3. Área de Upload Pública
st.subheader("1. Anexar Cotações dos Fornecedores (PDF)")
st.info("Arraste os PDFs. A Inteligência Artificial fará a leitura, cruzamento de itens, verificação fiscal (DIFAL/ST interestadual vs Local) e cálculo de frete.")
arquivos = st.file_uploader("Upload de Orçamentos", type=["pdf"], accept_multiple_files=True)

if arquivos:
    if not gemini_key:
        st.error("⚠️ Chave de IA do servidor não configurada. Adicione a GEMINI_API_KEY nos Secrets do Streamlit.")
    else:
        if st.button("🤖 Processar Análise Completa com IA", type="primary"):
            with st.spinner("A IA está interpretando os PDFs, cruzando os itens e simulando a carga tributária (Manaus vs Fora do Estado)..."):
                
                # Extração de texto dos PDFs
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

                # Prompt avançado para a IA analisar fornecedores, localização, impostos e frete
                prompt = f"""
                Você é um analista sênior de suprimentos e tributação fiscal com foco na Zona Franca de Manaus (Parente Andrade Ltda, Manaus/AM). 
                Analise os textos extraídos dos PDFs de cotação dos fornecedores abaixo.
                
                Regras obrigatórias para sua análise:
                1. Identifique o nome de cada fornecedor e a cidade/estado de origem informada na cotação (ou deduza pelo contexto). Se for de Manaus/AM, classifique como local. Se for de outro estado, classifique como interestadual.
                2. Padronize os itens equivalentes entre os orçamentos.
                3. Extraia a quantidade, unidade, preço unitário bruto, peso estimado do item em Kg e o NCM (se houver).
                4. Forneça uma análise comparativa inteligente apontando o melhor custo-benefício global.

                Retorne estritamente um objeto JSON válido, sem formatação markdown (sem ```json), exatamente neste formato:
                {{
                  "analise_geral": "Texto detalhado com a análise comparativa dos fornecedores, ressaltando vantagens e prazos.",
                  "fornecedores_info": [
                    {{
                      "nome": "Nome do Fornecedor 1",
                      "estado": "AM",
                      "local": true
                    }},
                    {{
                      "nome": "Nome do Fornecedor 2",
                      "estado": "SP",
                      "local": false
                    }}
                  ],
                  "itens": [
                    {{
                      "descricao": "Nome padronizado do item",
                      "unidade": "UN",
                      "quantidade": 10.0,
                      "peso_unitario_kg": 1.5,
                      "ncm": "8536.20.00",
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
                    client = genai.Client(api_key=gemini_key)
                    resposta = client.models.generate_content(
                        model='gemini-2.5-flash',
                        contents=prompt,
                    )
                    
                    texto_resposta = resposta.text.replace("```json", "").replace("```", "").strip()
                    dados_json = json.loads(texto_resposta)
                    
                    analise_texto = dados_json.get("analise_geral", "Análise concluída.")
                    fornecedores_objs = dados_json.get("fornecedores_info", [])
                    itens_IA = dados_json.get("itens", [])

                    # Exibe a Análise da IA
                    st.success("✅ Análise e Inteligência Tributária concluídas com sucesso!")
                    st.markdown("### 🧠 Parecer Técnico da IA")
                    st.info(analise_texto)
                    st.divider()

                    # Montagem da Tabela Comparativa de Custos Efetivos
                    tabela_dados = {
                        "Item": [i["descricao"] for i in itens_IA],
                        "NCM": [i.get("ncm", "N/D") for i in itens_IA],
                        "Unid.": [i["unidade"] for i in itens_IA],
                        "Qtd.": [i["quantidade"] for i in itens_IA],
                    }

                    fator_suframa = 1.0 - ((icms_suframa + pis_cofins) / 100.0)
                    totais_por_fornecedor = {}

                    for forn_info in fornecedores_objs:
                        forn_nome = forn_info["nome"]
                        is_local = forn_info.get("local", True)
                        
                        precos_efetivos = []
                        totais_efetivos = []
                        soma_total_forn = 0.0

                        for item in itens_IA:
                            p_base_raw = item.get("precos_unitarios", {}).get(forn_nome)
                            p_base = float(p_base_raw) if p_base_raw is not None else 0.0
                            peso = float(item.get("peso_unitario_kg") or 0.5)
                            q = float(item.get("quantidade") or 1.0)
                            
                            custo_unit = p_base
                            
                            if is_local:
                                # Fornecedor de Manaus/AM: Imposto 0 (operação interna incentivada / sem incidência adicional de frete FOB interestadual)
                                custo_unit = p_base
                            else:
                                # Fornecedor de Outro Estado: Aplica desoneração SUFRAMA/PIS-COFINS + Frete FOB proporcional + simulação de impacto tributário (DIFAL/ST)
                                custo_unit = custo_unit * fator_suframa
                                frete_proporcional = peso * frete_fob_kg
                                # Simulação de DIFAL / Substituição Tributária para uso/consumo ou revenda interestadual
                                difal_estimado = (aliquota_interna_am - 7.0) / 100.0 * p_base if aliquota_interna_am > 7.0 else 0.0
                                custo_unit += frete_proporcional + (difal_estimado * 0.2) # Impacto parcial de regulação

                            t_item = round(custo_unit * q, 2)
                            precos_efetivos.append(round(custo_unit, 2))
                            totais_efetivos.append(t_item)
                            soma_total_forn += t_item

                        tabela_dados[f"{forn_nome} (Unit. Efetivo)"] = precos_efetivos
                        tabela_dados[f"{forn_nome} (Total)"] = totais_efetivos
                        totais_por_fornecedor[forn_nome] = soma_total_forn

                    df_mapa = pd.DataFrame(tabela_dados)

                    st.subheader("2. Mapa Comparativo de Custo Efetivo (Equalizado com Impostos e Frete)")
                    st.markdown("*Para fornecedores locais (Manaus/AM): Impostos zerados. Para interestaduais: Considerado incentivo SUFRAMA, frete FOB por peso e impacto de DIFAL/ST.*")

                    def destacar_colunas(x):
                        df_estilo = pd.DataFrame('', index=x.index, columns=x.columns)
                        cores = ['#e6f2ff', '#f3f4f6', '#fffbeb', '#f0fdf4']
                        for idx, forn_info in enumerate(fornecedores_objs):
                            cor = cores[idx % len(cores)]
                            f_name = forn_info["nome"]
                            col_unit = f"{f_name} (Unit. Efetivo)"
                            col_tot = f"{f_name} (Total)"
                            if col_unit in df_estilo.columns:
                                df_estilo[col_unit] = f'background-color: {cor}'
                                df_estilo[col_tot] = f'background-color: {cor}'
                        return df_estilo

                    st.dataframe(
                        df_mapa.style.apply(destacar_colunas, axis=None).format(precision=2),
                        width='stretch',
                        hide_index=True
                    )

                    # Painel de Fechamento, Métricas e Sugestão do Vencedor
                    st.markdown("<br>", unsafe_allow_html=True)
                    cols = st.columns(len(fornecedores_objs) if len(fornecedores_objs) > 0 else 1)
                    
                    melhor_fornecedor = None
                    menor_valor = float('inf')

                    for idx, forn_info in enumerate(fornecedores_objs):
                        f_name = forn_info["nome"]
                        total_fornecedor = totais_por_fornecedor.get(f_name, 0.0)
                        
                        if total_fornecedor < menor_valor and total_fornecedor > 0:
                            menor_valor = total_fornecedor
                            melhor_fornecedor = f_name

                        with cols[idx]:
                            st.metric(label=f"Custo Total - {f_name}", value=f"R$ {total_fornecedor:,.2f}")
                            st.button(f"Gerar OC - {f_name}", key=f"btn_oc_{idx}", use_container_width=True)

                    # Destaque para o Vencedor Recomendado
                    if melhor_fornecedor:
                        st.markdown(f"""
                            <div class="winner-box">
                                <h3>🏆 Sugestão de Fornecedor Vencedor: <b>{melhor_fornecedor}</b></h3>
                                <p>Com base na equalização de impostos (ZFM/Suframa), incidência de frete FOB proporcional por peso e análise de itens, este fornecedor apresentou o <b>menor Custo Efetivo Total (R$ {menor_valor:,.2f})</b> para a Parente Andrade.</p>
                            </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Erro ao processar os dados com a IA: {e}")
else:
    st.info("👆 Faça o upload dos PDFs dos fornecedores para iniciar a equalização fiscal e logística automática.")
