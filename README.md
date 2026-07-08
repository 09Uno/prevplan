# Comparador de Calculos Previdenciarios

Mini SaaS interno para analise comparativa de calculos previdenciarios em cumprimento de sentenca.

O fluxo principal compara, de forma deterministica e auditavel:

- calculo do escritorio / autor;
- calculo ou impugnacao do INSS;
- calculo da contadoria judicial;
- processo completo, ZIP ou material misto, quando o usuario nao tiver os arquivos separados.

## Diretriz central

A extracao e a comparacao dos calculos ficam em regras e codigo, sem IA. A IA deve ser usada apenas na etapa final de redacao da minuta, consumindo o JSON estruturado ja apurado pelo backend.

## Estrutura

- `backend/`: API FastAPI, extracao de PDFs/planilhas/ZIP, segmentacao de processo completo, comparador deterministico e geracao de minuta.
- `frontend/`: interface Next.js para upload, visualizacao das divergencias, campos extraidos e minuta preliminar.
- `deploy/`: arquivos para publicacao com Docker, PostgreSQL e Caddy/HTTPS.
- `docs/`: arquitetura, seguranca, regras e material metodologico.

## Rodar em desenvolvimento

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
$env:INTERNAL_ACCESS_TOKEN = "bc-teste-27maio"
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Acesse:

```text
http://127.0.0.1:3000
```

## Publicar em dominio proprio

Use a pasta final `previdenciario-comparador-publicar` ou o arquivo `previdenciario-comparador-publicar.zip`.

Na VPS:

```bash
cp .env.example .env
nano .env
docker compose up -d --build
```

O Caddy publica o frontend no dominio definido em `DOMAIN` e emite HTTPS automaticamente.

## Principios de auditoria

1. Cada campo extraido guarda arquivo, pagina e trecho de evidencia quando disponivel.
2. Divergencias sao classificadas por regra explicita.
3. O JSON da comparacao e a fonte de verdade para a minuta.
4. A minuta preliminar nao recalcula valores; apenas redige a partir das divergencias apuradas.
