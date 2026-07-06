# Publicacao temporaria para testes

Este projeto pode ser exposto temporariamente via tunnel para validacao externa. Nao e uma configuracao de producao.

## Comandos usados

Backend protegido por token:

```powershell
$env:INTERNAL_ACCESS_TOKEN = "trocar-este-token"
cd "C:\Users\laura\OneDrive\ARQUIVOS GERAIS\MENTORIA\previdenciario-comparador\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend com proxy para o backend:

```powershell
cd "C:\Users\laura\OneDrive\ARQUIVOS GERAIS\MENTORIA\previdenciario-comparador\frontend"
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Tunnel publico temporario preferencial:

```powershell
cd "C:\Users\laura\OneDrive\ARQUIVOS GERAIS\MENTORIA\previdenciario-comparador"
npx --yes cloudflared tunnel --url http://127.0.0.1:3000
```

Alternativa por localtunnel:

```powershell
cd "C:\Users\laura\OneDrive\ARQUIVOS GERAIS\MENTORIA\previdenciario-comparador"
npx --yes localtunnel --port 3000 --local-host 127.0.0.1
```

## Como testar

1. Abrir a URL `https://...loca.lt`.
2. Preencher o token de acesso no canto superior direito.
3. Enviar PDF, XLSX, CSV ou ZIP.
4. Clicar em `Analisar deterministicamente`.

## Cuidados

- O link funciona apenas enquanto o processo do tunnel estiver aberto.
- O computador local precisa permanecer ligado e conectado.
- Use apenas com pessoas autorizadas, porque os arquivos trafegam ate esta maquina.
- Para producao, substituir por deploy com HTTPS, login real, Postgres, storage privado, logs auditaveis e politica de retencao.
