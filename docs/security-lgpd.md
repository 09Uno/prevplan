# Seguranca e LGPD

## Dados sensiveis

Os documentos podem conter CPF, NB, dados medicos/beneficiarios, valores de beneficio e historico processual. Em producao:

- criptografia em repouso para arquivos e banco;
- TLS obrigatorio;
- controle de acesso por usuario interno;
- logs sem conteudo integral de documentos;
- trilha de auditoria por caso, usuario, regra e versao;
- politica de retencao por processo.

## IA

Usar IA apenas na camada de minuta. A API escolhida deve garantir nao treinamento com os dados enviados e uma politica de retencao compativel com a operacao do escritorio.

Padrao recomendado:

- enviar somente `ComparisonResult`;
- remover anexos brutos do prompt;
- registrar modelo, data, prompt-template e hash do JSON;
- exigir revisao humana antes de protocolo.

