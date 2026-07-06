# Deploy em dominio proprio

Este pacote deixa o SaaS pronto para subir em um servidor Linux com Docker, apontar um dominio e gravar os planejamentos em PostgreSQL.

## 1. Preparar o servidor

No servidor, instale Docker e Docker Compose. Depois copie a pasta `previdenciario-comparador` inteira para o servidor.

O DNS do dominio deve apontar para o IP do servidor:

- Tipo: `A`
- Nome: `previdenciario` ou o subdominio escolhido
- Valor: IP publico do servidor

## 2. Configurar variaveis

Na raiz do projeto:

```bash
cp .env.example .env
nano .env
```

Troque principalmente:

- `DOMAIN`: seu dominio ou subdominio.
- `INTERNAL_ACCESS_TOKEN`: token forte para acessar o app.
- `POSTGRES_PASSWORD`: senha forte do banco.
- `DATABASE_URL`: manter igual ao exemplo, alterando apenas usuario/senha/banco se voce mudar os campos.

## 3. Subir

```bash
docker compose up -d --build
```

O Caddy publica o frontend no dominio e emite HTTPS automaticamente. A API fica atras do frontend via `/api`.

## 4. Banco de dados

O schema inicial esta em `deploy/postgres/schema.sql`.

Tabelas criadas:

- `planning_cases`: planejamentos previdenciarios completos em JSON auditavel.
- `comparison_cases`: compatibilidade com o comparador antigo.

Se voce for usar um banco externo, altere `DATABASE_URL` no `.env` e remova ou ignore o servico `db` no `docker-compose.yml`.

Formato esperado:

```env
DATABASE_URL=postgresql://usuario:senha@host:5432/nome_do_banco
```

## 5. Comandos uteis

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose ps
docker compose down
```

Backup simples do banco local:

```bash
docker compose exec db pg_dump -U previdenciario previdenciario > backup-previdenciario.sql
```

## 6. Segurança

- Nao suba o arquivo `.env` para repositorio publico.
- Use `INTERNAL_ACCESS_TOKEN` forte.
- Restrinja acesso ao servidor por SSH com chave.
- Configure rotina de backup do volume `postgres_data`.
