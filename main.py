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

st.title("🛒 CotaMap - Equalização de Preços & Calculadora DIFAL / ST")
st.markdown("**Sistema de Suprimentos | Parente Andrade Ltda (Manaus - AM)**")
st.divider()

# 2. Parâmetros Fiscais e Logísticos Globais (Pós-Proposta)
st.sidebar.header("⚙️ Parâmetros de Equalização")
aliquota_destino = st.sidebar.number_input("Alíquota Interna Destino (AM %)", value=20.0, step=0.5) / 100.0
aliquota_origem = st.sidebar.number_input("Alíquota Interestadual Origem (%)", value=7.0, step=1.0) / 100.0
fcp_percentual = st.sidebar.number_input("Fundo de Combate à Pobreza (FCP %)", value=2.0, step=0.5) / 100.0

# Resgate seguro da chave de IA oculta no servidor
try:
    gemini_key = st.secrets["GEMINI_API_KEY"]
except:
    gemini_key = os.environ.get("GEMINI_API_KEY", "")

# 3. Área de Upload das Propostas Brutas
st.subheader("1. Anexar Propostas dos Fornecedores (PDF)")
st.info("Faça o upload dos PDFs das propostas. A IA fará a leitura dos valores brutos e, em seguida, o sistema executará a conta minuciosa de equalização intermunicipal (Frete, ICMS ST, DIFAL e Descontos).")
arquivos = st.file_uploader("Upload de Orçamentos", type=["pdf"], accept_multiple_files=True)

if arquivos:
    if not gemini_key:
        st.error("⚠️ Chave de IA do servidor não configurada. Adicione a GEMINI_API_KEY nos Secrets do Streamlit.")
    else:
        if st.button("📊 Processar Propostas e Executar Equalização", type="primary"):
            with st.spinner("Lendo propostas, estruturando itens e calculando encargos fiscais e fretes..."):
                
                # Extração de texto dos PDFs de propostas
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

                # Prompt para extrair os dados brutos das propostas
                prompt = f"""
                Você é um analista sênior de suprimentos da Parente Andrade Ltda (Manaus/AM). 
                Analise os textos extraídos dos PDFs de propostas comerciais enviadas por diferentes fornecedores.
                
                Instruções:
                1. Identifique o nome de cada fornecedor e o estado/cidade de origem constante na proposta.
                2. Padronize os itens descritos nas propostas para permitir a comparação lado a lado.
                3. Extraia a quantidade, unidade, preço unitário bruto proposto, NCM, prazo de entrega e condição de pagamento.

                Retorne estritamente um objeto JSON válido, sem formatação markdown (sem ```json), exatamente neste formato:
                {{
                  "analise_propostas": "Parecer detalhado comparando as propostas enviadas.",
                  "fornecedores_info": [
                    {{
                      "nome": "DIGITRON",
                      "cidade_estado": "Manaus - AM",
                      "local": true,
                      "condicao_pagamento": "A VISTA",
                      "prazo_entrega": "25 DIAS ÚTEIS"
                    }},
                    {{
                      "nome": "TOLEDO",
                      "cidade_estado": "São Paulo - SP",
                      "local": false,
                      "condicao_pagamento": "30 DDL",
                      "prazo_entrega": "60 DIAS"
                    }}
                  ],
                  "itens": [
                    {{
                      "descricao": "BALANÇA 1000KGS",
                      "unidade": "UN",
                      "quantidade": 1.0,
                      "ncm": "8423.82.00",
                      "precos_unitarios_brutos": {{
                        "DIGITRON": 6950.00,
                        "TOLEDO": 16980.00
                      }}
                    }}
                  ]
                }}

                Textos das propostas:
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
                    
                    analise_texto = dados_json.get("analise_propostas", "Propostas processadas.")
                    fornecedores_objs = dados_json.get("fornecedores_info", [])
                    itens_IA = dados_json.get("itens", [])

                    st.success("✅ Leitura e estruturação das propostas concluídas!")
                    st.markdown("### 📋 Parecer de Análise Comercial")
                    st.info(analise_texto)
                    st.divider()

                    # Exibição interativa para ajuste dos encargos por fornecedor (igual à planilha de referência)
                    st.subheader("2. Matriz de Equalização Intermunicipal (Impostos, Frete e Descontos)")
                    st.markdown("*Insira abaixo os valores de Frete, Descontos, ICMS ST e DIFAL apurados para cada proposta (seguindo o modelo da sua planilha de cálculo).*")

                    fornecedores_resultados = {}
                    colunas_forn = st.columns(len(fornecedores_objs) if len(fornecedores_objs) > 0 else 1)

                    for idx, forn_info in enumerate(fornecedores_objs):
                        f_name = forn_info["nome"]
                        is_local = forn_info.get("local", True)
                        
                        with colunas_forn[idx]:
                            st.markdown(f"#### 🏢 {f_name}")
                            st.caption(f"Origem: {forn_info.get('cidade_estado', 'Desconhecida')}")
                            
                            # Calcula o total bruto inicial dos itens para este fornecedor
                            total_bruto_f = sum([float(i.get("precos_unitarios_brutos", {}).get(f_name, 0.0)) * float(i.get("quantidade", 1.0)) for i in itens_IA])
                            st.metric(label="Total Bruto", value=f"R$ {total_bruto_f:,.2f}")

                            # Campos ajustáveis idênticos à planilha de Excel
                            desc_perc = st.number_input(f"Desconto (%) - {f_name}", value=0.0, step=1.0, key=f"desc_{idx}") / 100.0
                            
                            if is_local:
                                st.info("ℹ️ Fornecedor Local (Manaus/AM): ICMS ST e DIFAL = 0%")
                                icms_st_val = 0.0
                                difal_val = 0.0
                                frete_val = st.number_input(f"Frete Local (R$) - {f_name}", value=0.0, step=100.0, key=f"frete_{idx}")
                            else:
                                st.warning("⚠️ Fornecedor Interestadual: Sujeito a DIFAL, ST e Frete FOB")
                                icms_st_val = st.number_input(f"ICMS ST (Fator/Alíquota) - {f_name}", value=0.7, step=0.1, key=f"st_{idx}")
                                
                                # Cálculo automático de DIFAL baseado na calculadora padrão
                                base_difal = total_bruto_f * (1.0 - desc_perc)
                                difal_calculado = base_difal * (aliquota_destino - aliquota_origem + fcp_percentual)
                                difal_val = st.number_input(f"DIFAL (R$) - {f_name}", value=round(difal_calculado, 2), step=100.0, key=f"difal_{idx}")
                                
                                frete_val = st.number_input(f"Frete FOB (R$) - {f_name}", value=3200.0, step=100.0, key=f"frete_{idx}")

                            # Total Geral Equalizado para o fornecedor
                            total_liquido = total_bruto_f * (1.0 - desc_perc)
                            total_geral_forn = total_liquido + frete_val + difal_val
                            
                            fornecedores_resultados[f_name] = {
                                "total_bruto": total_bruto_f,
                                "desconto": total_bruto_f * desc_perc,
                                "liquido": total_liquido,
                                "st": icms_st_val,
                                "difal": difal_val,
                                "frete": frete_val,
                                "total_geral": total_geral_forn,
                                "pagamento": forn_info.get("condicao_pagamento", "N/D"),
                                "entrega": forn_info.get("prazo_entrega", "N/D")
                            }

                    st.divider()
                    st.subheader("3. Mapa Comparativo Consolidado e Sugestão de Vencedor")

                    # Montagem da tabela consolidada idêntica à planilha de Cotação
                    tabela_comparativa = []
                    melhor_fornecedor = None
                    menor_valor_geral = float('inf')

                    for f_name, res in fornecedores_resultados.items():
                        if res["total_geral"] < menor_valor_geral and res["total_geral"] > 0:
                            menor_valor_geral = res["total_geral"]
                            melhor_fornecedor = f_name

                        tabela_comparativa.append({
                            "Fornecedor": f_name,
                            "Valor Total Bruto": res["total_bruto"],
                            "Desconto": res["desconto"],
                            "Valor Líquido": res["liquido"],
                            "ICMS ST / Ajuste": res["st"],
                            "DIFAL / Encargos": res["difal"],
                            "Frete": res["frete"],
                            "TOTAL GERAL": res["total_geral"],
                            "Cond. Pagamento": res["pagamento"],
                            "Prazo Entrega": res["entrega"]
                        })

                    df_resumo = pd.DataFrame(tabela_comparativa)

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

                    # Destaque do Fornecedor Vencedor Recomendado
                    if melhor_fornecedor:
                        st.markdown(f"""
                            <div class="winner-box">
                                <h3>🏆 Sugestão de Fornecedor Vencedor: <b>{melhor_fornecedor}</b></h3>
                                <p>Após aplicar a conta minuciosa de equalização intermunicipal (somando frete, abatendo descontos e computando os encargos de DIFAL/ST para operações interestaduais), o fornecedor que apresentou o <b>menor Custo Total Geral é {melhor_fornecedor} (R$ {menor_valor_geral:,.2f})</b>.</p>
                            </div>
                        """, unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Erro ao processar as propostas com a IA: {e}")
else:
    st.info("👆 Faça o upload dos PDFs das propostas recebidas para iniciar a equalização e o comparativo intermunicipal.")
