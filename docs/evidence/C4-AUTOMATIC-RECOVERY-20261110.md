# C4 — Recuperação da reprodução automática — 2026-11-10

- `python3 tests/client/automatic-recovery-test.py`: PASS (13,96 s).
- Cliente Qt nativo com cache isolado, formato 4 e duas páginas, sem servidor.
- SIGKILL: supervisor reiniciou cliente, recebeu frames e cliente avançou à página 2.
- SIGSTOP: PID permaneceu vivo; supervisor detectou frames estagnados, encerrou
  processo, reiniciou e cliente avançou novamente à página 2.
- Hash do cache permaneceu íntegro. Parada do supervisor removeu registro do filho.
- Sintaxe Bash do novo lançador e `git diff --check`: PASS.

Lançador Fedora combina build único, opções de distribuição e supervisor existente.
Não instala inicialização automática na estação nem altera perfil físico Pi 5.
Sem validação de boot ou hardware nesta entrega.

[Uso](../client/supervised-playback.md).
