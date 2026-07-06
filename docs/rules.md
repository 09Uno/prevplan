# Regras iniciais de comparacao

Este arquivo documenta as regras codificadas. Cada regra nova deve ter:

- identificador;
- hipotese objetiva;
- campos usados;
- fundamento juridico/tecnico;
- severidade;
- exemplos reais anonimizados.

## Campos comparados no MVP

- `rmi`: renda mensal inicial.
- `dib`: data de inicio do beneficio.
- `dip`: data de inicio de pagamento.
- `calculation_until`: competencia/data final de atualizacao.
- `correction_index`: IPCA-E, INPC, SELIC, TR.
- `interest_rate`: percentual ou SELIC.
- `principal`, `arrears`, `abatements`, `honoraries`, `total`.

## Regras juridicas iniciais

### EC113_INDEX_001

Se o documento menciona TR/taxa referencial em contexto de EC 113/2021, sinalizar possivel aplicacao indevida apos 09/12/2021.

Status: alerta conservador, exige validacao do corte temporal.

### EC113_INDEX_002

Se o documento menciona IPCA-E e SELIC simultaneamente, sinalizar necessidade de conferir o corte temporal antes/depois da EC 113/2021.

Status: alerta conservador, nao presume erro.

### INTEREST_001

Se o documento menciona juros negativos, sinalizar materia para conferencia tecnica, especialmente em abatimentos ou pagamentos administrativos.

### HONOR_OFFSET_001

Se o documento relaciona seguro-desemprego/abatimentos e honorarios, sinalizar necessidade de conferir se a deducao afetou indevidamente a base honoraria.

