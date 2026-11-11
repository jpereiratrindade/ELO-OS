# Fundação de consumíveis Sister-Studio — 2026-11-11

## Alteração demonstrada

Documento ELO-SISTER-BASES-001 v0.1.0 incorporado byte a byte do arquivo fornecido.
ADR-011 adota responsabilidades e detalha identidade por instância autenticada,
conflito de manifesto e fixação de versões em bundles. Implementado pré-validador
somente leitura do perfil inicial PCM WAV e JSON Schema Draft 2020-12.

## Verificação executada no host

- `cmp` entre documento fornecido e cópia versionável: saída 0.
- `python3 tests/network/consumable-test.py`: 6 testes aprovados, com subcasos de
  corrupção, metadados inválidos, truncamento, traversal, symlink, FIFO e arquivos
  extras; CLI retorna códigos distintos para sucesso e falha.
- `./tests/smoke.sh`: saída 0, incluindo novo teste de consumíveis e regressões
  existentes de importação, cliente local, supervisor, painel e ferramentas.
- Schema verificado com `jsonschema.Draft202012Validator.check_schema` e validado
  contra o manifesto da fixture PCM real gerada pelo teste. `jsonschema` usado
  apenas nesta verificação de desenvolvimento; CLI e smoke usam biblioteca padrão.
- Links locais dos novos documentos conferidos; `git diff --check` sem erros.

Arquivo WAV malformado provocou `RuntimeError` no leitor Python durante o primeiro
ensaio. O validador agora converte essa falha em rejeição de pacote; teste passou.

## Limites

Sem alterações em serviços instalados, credenciais ou repositórios externos.
Nenhum endpoint de ingestão nem catálogo foi implementado. Validação local não é
recibo de aceitação, autenticação de origem ou aprovação de direitos. G1–G9 e
experimento vertical integrado continuam pendentes. Sem homologação de Pi física.
