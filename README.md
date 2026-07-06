# Planejamento Previdenciario

Mini SaaS interno para automatizar a triagem documental, os cenarios de aposentadoria e a geracao revisavel de parecer/planejamento previdenciario no padrao do escritorio.

O projeto preserva uma diretriz central: numeros, datas, regras e divergencias sao tratados por pipeline deterministico e auditavel. A IA deve entrar apenas na leitura assistida e redacao controlada, consumindo o JSON estruturado produzido pelo motor.

## Estrutura

- `backend/`: API FastAPI, extracao de PDFs/planilhas/ZIP, classificacao de documentos, motor RGPS 2026 e geracao `.docx`.
- `frontend/`: interface interna em Next.js para dados do segurado, upload de documentos, cenarios, pendencias e parecer.
- `docs/`: arquitetura, regras juridico-contabeis e orientacoes LGPD/infra.

## Rodar em desenvolvimento

Backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .[dev]
uvicorn app.main:app --reload --port 8000
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

A interface assume a API em `http://127.0.0.1:8000` por rewrite do Next. Para mudar, defina `BACKEND_URL`.

## Subir em dominio proprio

Os arquivos de deploy ficam prontos na raiz:

- `.env.example`: modelo de variaveis para dominio, token e banco.
- `docker-compose.yml`: frontend, backend, PostgreSQL e Caddy com HTTPS.
- `backend/Dockerfile` e `frontend/Dockerfile`: imagens de producao.
- `deploy/postgres/schema.sql`: schema inicial do banco.
- `deploy/README_DEPLOY.md`: passo a passo para servidor e DNS.

Para usar banco externo, basta configurar `DATABASE_URL`. Sem `DATABASE_URL`, o backend continua usando memoria local para desenvolvimento.

## MVP implementado

1. Upload de documentos soltos ou ZIP.
2. Classificacao inicial de CNIS, CTPS, PPP, LTCAT, CTC, documento de identificacao e parecer.
3. Motor RGPS deterministico com regras da EC 103/2019: pontos, idade minima progressiva, idade, pedagio 50% e pedagio 100%.
4. Tabela INSS 2026 com teto de R$ 8.475,55 e aliquota progressiva de empregado.
5. Pendencias de CNIS, atividade especial sem PPP, lacunas, remuneracao pos-fim e revisao de pedagio.
6. Parecer em Markdown e download `.docx`.

## Principios de auditoria

1. Cada campo extraido guarda pagina, arquivo e trecho de evidencia.
2. Divergencias sao classificadas por regra explicita, nunca por interpretacao de LLM.
3. O JSON da comparacao e a fonte de verdade para a minuta.
4. A minuta preliminar nao recalcula valores; apenas redige a partir das divergencias ja apuradas.
