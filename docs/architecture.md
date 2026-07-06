# Arquitetura

## Camadas

1. **Ingestao deterministica**
   - PDF: `PyMuPDF` para texto paginado; `pdfplumber/camelot` podem entrar depois para tabelas.
   - PDF completo do PJe: segmentacao por marcador `Num. <id> - Pag. 1`, com heranca de fonte para anexos de calculo que aparecem logo apos a peca principal.
   - Planilhas: `pandas/openpyxl`, preservando aba, linha e coluna.
   - Saida: `ExtractedCalculation`, sempre com `EvidenceRef`.

2. **Normalizacao e comparacao deterministica**
   - Campos canonicos: RMI, DIB, DIP, marco final, indice, juros, principal, atrasados, abatimentos, honorarios e total.
   - Comparacao campo a campo com tolerancia monetaria de R$ 0,01.
   - Regras juridicas codificadas em `backend/app/comparison/rules.py`.

3. **Redacao assistida**
   - Entrada unica: `ComparisonResult`.
   - A IA nao recebe PDFs brutos por padrao, nao recalcula e nao classifica divergencias.
   - Sem `ANTHROPIC_API_KEY`, o sistema gera minuta por template.

## Persistencia

O MVP usa repositorio em memoria para desenvolvimento. A migracao natural e Postgres com tabelas:

- `cases`
- `documents`
- `extracted_calculations`
- `field_evidence`
- `comparison_results`
- `drafts`
- `audit_events`

## Fronteira de seguranca

Documentos sensiveis devem ficar em storage privado, criptografado, com controle de acesso por usuario interno. O historico precisa guardar hash do texto extraido e versao das regras aplicadas, para reproduzir a conclusao tecnica.
