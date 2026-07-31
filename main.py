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

st.title("🛒 CotaMap - Mapa de Cotação Inteligente & Equalização Fiscal")
st.markdown("**Sistema de Suprimentos | Parente Andrade Ltda (Manaus - AM)**")
st.divider()

# 2. Parâmetros Fiscais e Logísticos para Equalização Pós-Proposta
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

# 3. Área de Upload das Propostas Recebidas
st.subheader("1. Anexar Propostas dos Fornecedores (PDF)")
st.info("Faça o upload dos PDFs das propostas recebidas. Após o envio, o sistema fará a leitura, cruzamento dos itens e a conta minuciosa de equalização intermunicipal.")
arquivos = st.file_uploader("Upload de Orçamentos", type=["pdf"], accept_multiple_files=True)

if arquivos:
    if not gemini_key:
        st.error("⚠️ Chave de IA do servidor não configurada. Adicione a GEMINI_API_KEY nos Secrets do Streamlit.")
    else:
        if st.button("📊 Processar Propostas e Executar Conta Minuciosa", type="primary"):
            with st.spinner("Lendo propostas enviadas, cruzando itens e calculando os encargos intermunicipais e fretes..."):
                
                # Extração do texto de todas as propostas enviadas
                texto_completo_pdfs = ""
                for arquivo in arquivos:
                    texto_completo_pdfs += f"\n\n--- PROPOSTA / FORNECEDOR / ARQUIVO: {arquivo.name} ---\n"
                    try:
                        with pdfplumber.open(arquivo) as pdf:
                            for pagina in pdf.pages:
                                extraido = pagina.extract_text()
                                if extraido:
                                    texto_completo_pdfs += extraido + "\n"
                    except Exception as e:
                        st.error(f"Erro ao ler {arquivo.name}: {e}")

                prompt = f"""
                Você é um analista sênior de suprimentos e fiscal de Parente Andrade Ltda (Manaus/AM). 
                Analise os textos extraídos dos PDFs de propostas enviadas por diferentes fornecedores.
                
                Instruções:
                1. Identifique o nome de cada fornecedor e o estado/cidade de origem constante na proposta.
                2. Padronize os itens descritos nas propostas para permitir a comparação direta.
                3. Extraia a quantidade, unidade, preço unitário bruto proposto, NCM (se houver) e estime o peso unitário em Kg de cada item.

                Retorne estritamente um objeto JSON válido, sem formatação markdown (sem ```json), exatamente neste formato:
                {{
                  "analise_propostas": "Parecer detalhado comparando as propostas enviadas, indicando as condições de pagamento e prazos.",
                  "fornecedores_info": [
                    {{
                      "nome": "Nome do Fornecedor 1",
                      "cidade_estado": "Manaus - AM",
                      "local": true
                    }},
                    {{
                      "nome": "Nome do Fornecedor 2",
                      "cidade_estado": "São Paulo - SP",
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
                      "precos_unitarios_brutos": {{
                        "Nome do Fornecedor 1": 150.00,
                        "Nome do Fornecedor 2": 145.50
                      }}
                    }}
                  ]
                }}

                Textos das propostas enviadas:
                {texto_completo_pdfs}
                """

                try:
                    # Chamada utilizando o modelo ativo e estável gemini-3.6-flash
                    client = genai.Client(api_key=gemini_key)
                    resposta = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=prompt,
                    )
                    
                    texto_resposta = resposta.text.replace("```json", "").replace("```", "").strip()
                    dados_json = json.loads(texto_resposta)
                    
                    analise_texto = dados_json.get("analise_propostas", "Propostas processadas.")
                    fornecedores_objs = dados_json.get("fornecedores_info", [])
                    itens_IA = dados_json.get("itens", [])

                    st.success("✅ Propostas processadas e equalizadas com sucesso!")
                    st.markdown("### 📋 Parecer de Análise das Propostas")
                    st.info(analise_texto)
                    st.divider()

                    tabela_dados = {
                        "Item": [i["descricao"] for i in itens_IA],
                        "NCM": [i.get("ncm", "N/D") for i in itens_IA],
                        "Unid.": [i["unidade"] for i in itens_IA],
                        "Qtd.": [i["quantidade"] for i in itens_IA],
                    }

                    totais_por_fornecedor = {}
                    fator_suframa_pis = 1.0 - ((icms_suframa + pis_cofins) / 100.0)

                    for forn_info in fornecedores_objs:
                        forn_nome = forn_info["nome"]
                        is_local = forn_info.get("local", True)
                        
                        precos_efetivos = []
                        totais_efetivos = []
                        soma_total_forn = 0.0

                        for item in itens_IA:
                            p_bruto_raw = item.get("precos_unitarios_brutos", {}).get(forn_nome)
                            p_bruto = float(p_bruto_raw) if p_bruto_raw is not None else 0.0
                            peso = float(item.get("peso_unitario_kg") or 0.5)
                            q = float(item.get("quantidade") or 1.0)
                            
                            custo_final = p_bruto
                            
                            if is_local:
                                # Fornecedor de Manaus/AM: Imposto 0 (operação interna sem DIFAL/ST e sem frete FOB interestadual)
                                custo_final = p_bruto
                            else:
                                # Fornecedor de Outro Estado: Executa a conta minuciosa intermunicipal
                                base_incentivada = p_bruto * fator_suframa_pis
                                frete_item = peso * frete_fob_kg
                                difal_st = (aliquota_interna_am - 7.0) / 100.0 * p_bruto if aliquota_interna_am > 7.0 else 0.0
                                
                                custo_final = base_incentivada + frete_item + (difal_st * 0.25)

                            t_item = round(custo_final * q, 2)
                            precos_efetivos.append(round(custo_final, 2))
                            totais_efetivos.append(t_item)
                            soma_total_forn += t_item

                        tabela_dados[f"{forn_nome} (Unit. Equalizado)"] = precos_efetivos
                        tabela_dados[f"{forn_nome} (Total Final)"] = totais_efetivos
                        totais_por_fornecedor[forn_nome] = soma_total_forn

                    df_mapa = pd.DataFrame(tabela_dados)

                    st.subheader("2. Mapa Comparativo de Custos Pós-Proposta (Conta Minuciosa Intermunicipal)")
                    st.markdown("*Demonstrativo com a aplicação de imposto zero para fornecedores locais de Manaus e equalização completa (Suframa, Frete FOB e DIFAL/ST) para os demais estados.*")

                    def destacar_colunas(x):
                        df_estilo = pd.DataFrame('', index=x.index, columns=x.columns)
                        cores = ['#e6f2ff', '#f3f4f6', '#fffbeb', '#f0fdf4']
                        for idx, forn_info in enumerate(fornecedores_objs):
                            cor = cores[idx % len(cores)]
                            f_name = forn_info["nome"]
                            col_unit = f"{f_name} (Unit. Equalizado)"
                            col_tot = f"{f_name} (Total Final)"
                            if col_unit in df_estilo.columns:
                                df_estilo[col_unit] = f'background-color: {cor}'
                                df_estilo[col_tot] = f'background-color: {cor}'
                        return df_estilo

                    st.dataframe(
                        df_mapa.style.apply(destacar_colunas, axis=None).format(precision=2),
                        width='stretch',
                        hide_index=True
                    )

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
                            st.metric(label=f"Total Final - {f_name}", value=f"R$ {total_fornecedor:,.2f}")
                            st.button(f"Gerar OC - {f_name}", key=f"btn_oc_{idx}", use_container_width=True)

                    if melhor_fornecedor:
                        st.markdown(f"""
                            <div class="winner-box">
                                <h3>🏆 Sugestão de Fornecedor Vencedor: <b>{melhor_fornecedor}</b></h3>
                                <p>Após a análise das propostas e a conta minuciosa de equalização fiscal intermunicipal (considerando isenção local ou encargos de frete FOB, Suframa e DIFAL para outros estados), o fornecedor com o <b>menor Custo Efetivo Total é {melhor_fornecedor} (R$ {menor_valor:,.2f})</b>.</p>
                            </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Erro ao processar as propostas com a IA: {e}")
else:
    st.info("👆 Faça o upload dos PDFs das propostas recebidas para iniciar a equalização e comparação intermunicipal.")
