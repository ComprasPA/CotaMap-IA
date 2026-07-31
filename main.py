import os
import json
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from anthropic import Anthropic
import pdfplumber

# Inicializa o app FastAPI
app = FastAPI(title="CotaMap API", description="Motor de IA para extração de cotações")

# Permite conexões externas (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rota visual simples para você testar o upload direto pelo navegador
@app.get("/", response_class=HTMLResponse)
async def pagina_inicial():
    return """
    <html>
        <head><title>CotaMap - Teste IA</title></head>
        <body style="font-family: sans-serif; padding: 40px;">
            <h2>Upload de Cotação (Teste Rápido)</h2>
            <form action="/api/extrair" enctype="multipart/form-data" method="post">
                <input name="file" type="file" accept="application/pdf">
                <input type="submit" value="Enviar para a IA">
            </form>
        </body>
    </html>
    """

@app.post("/api/extrair")
async def extrair_cotacao(file: UploadFile = File(...)):
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Por favor, envie um arquivo PDF.")

    texto_extraido = ""
    
    try:
        # Lê o PDF 
        with pdfplumber.open(file.file) as pdf:
            for pagina in pdf.pages:
                texto = pagina.extract_text()
                if texto:
                    texto_extraido += texto + "\n"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao ler PDF: {str(e)}")

    if not texto_extraido.strip():
        raise HTTPException(status_code=400, detail="O PDF parece ser uma imagem sem texto.")

    # Busca a chave da API (você precisará configurar isso no seu ambiente)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="Chave ANTHROPIC_API_KEY não configurada.")

    client = Anthropic(api_key=api_key)

    PROMPT = f"""
    Você é um especialista em compras industriais e de construção.
    Analise o documento de cotação abaixo e extraia os dados em JSON.

    Retorne APENAS um JSON válido, sem formatação, sem texto antes ou depois:
    {{
      "fornecedor": "nome da empresa",
      "cnpj": "XX.XXX.XXX/XXXX-XX ou null",
      "uf": "sigla do estado (SP, PA, MA, etc.)",
      "itens": [
        {{
          "descricao": "descrição do item",
          "quantidade": 1.0,
          "precoUnitario": 10.50,
          "precoTotal": 10.50
        }}
      ]
    }}

    Documento da cotação:
    {texto_extraido}
    """

    try:
        resposta = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=4096,
            temperature=0.1,
            messages=[{"role": "user", "content": PROMPT}]
        )
        
        return json.loads(resposta.content[0].text)

    except Exception as e:
        print(f"Erro na API da Anthropic: {e}")
        raise HTTPException(status_code=500, detail="Falha ao extrair dados via IA.")
