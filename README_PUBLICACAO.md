# Publicacao em dominio proprio

Esta pasta contem o mini SaaS pronto para publicar em uma VPS com Docker.

## O que esta incluido

- `frontend/`: interface web em Next.js.
- `backend/`: API FastAPI com extracao, regras deterministicas e geracao de documentos.
- `deploy/Caddyfile`: proxy HTTPS automatico para o dominio.
- `deploy/postgres/schema.sql`: schema inicial do PostgreSQL.
- `docker-compose.yml`: sobe banco, backend, frontend e Caddy.
- `.env.example`: modelo das variaveis de producao.

## 1. Apontar o dominio

No painel DNS do dominio, crie um registro:

```text
Tipo: A
Nome: app ou o subdominio escolhido
Valor: IP publico da VPS
```

Exemplo: `previdenciario.seudominio.com.br -> 123.123.123.123`.

## 2. Enviar a pasta para a VPS

Copie esta pasta inteira para o servidor. Exemplo:

```bash
scp -r previdenciario-comparador-publicar usuario@IP_DA_VPS:/opt/previdenciario-comparador
```

No servidor:

```bash
cd /opt/previdenciario-comparador
```

## 3. Criar o arquivo `.env`

```bash
cp .env.example .env
nano .env
```

Preencha:

```env
DOMAIN=previdenciario.seudominio.com.br
INTERNAL_ACCESS_TOKEN=um-token-grande-e-secreto
POSTGRES_PASSWORD=uma-senha-forte
DATABASE_URL=postgresql://previdenciario:uma-senha-forte@db:5432/previdenciario
ANTHROPIC_API_KEY=
```

Se for usar a geracao de minuta por IA, preencha `ANTHROPIC_API_KEY`.

## 4. Subir o sistema

```bash
docker compose up -d --build
```

O Caddy emite o certificado HTTPS automaticamente quando o DNS ja estiver apontando para a VPS.

## 5. Testar

Abra:

```text
https://SEU_DOMINIO
```

Use o token definido em `INTERNAL_ACCESS_TOKEN`.

## 6. Comandos uteis

Ver status:

```bash
docker compose ps
```

Ver logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f caddy
```

Reiniciar:

```bash
docker compose restart
```

Atualizar depois de alterar arquivos:

```bash
docker compose up -d --build
```

Backup simples do banco:

```bash
docker compose exec db pg_dump -U previdenciario previdenciario > backup-previdenciario.sql
```

## Observacoes importantes

- Nao envie `.env` para repositorio publico.
- Use token e senha fortes.
- Mantenha backups do banco.
- Para uso real com dados sensiveis, prefira VPS propria, SSH por chave e firewall liberando apenas portas `80`, `443` e `22`.
