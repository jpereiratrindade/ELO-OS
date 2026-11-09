# P2 — protótipos locais, entrega sem compilação

- Data local: 2026-11-08, Fedora 44 x86_64.
- Escopo: código de contratos/adaptadores e testes locais de ativação/supervisão; próxima compilação transferida pelo mantenedor para o desktop.
- A compilação gráfica em andamento foi encerrada por SIGTERM no grupo próprio, sem apagar downloads, objetos ou fontes. Não havia imagem gráfica concluída; não foi executado boot QEMU GUI.
- Não foram executados compiladores C++, Qt ou Buildroot após essa orientação. O commit usa `[skip ci]`; nenhum PASS remoto de uma revisão anterior é atribuído a esta entrega.

## Verificação desta entrega

Resultados executados antes do commit, na árvore de trabalho desta entrega:

| Verificação | Resultado | Duração observada |
| --- | --- | --- |
| Q0 estrutura, sintaxe e links | PASS | Sem medição separada |
| Pré-checagem Pi 5, testes Python | 9/9 PASS | 0,017 s |
| Ativação local, testes Python | 11/11 PASS | 0,262 s |
| Supervisor, shell do Fedora | 8/8 PASS | 7,515 s |
| Supervisor, BusyBox ash/applets existentes | 8/8 PASS | 6,735 s |
| `git diff --check` | PASS | Sem medição separada |

Durações do executor em host compartilhado; não são benchmark de boot, recuperação Qt ou Pi 5. Os comandos usados foram:

```bash
./tests/smoke.sh
ELO_SUPERVISOR_SHELL="$PWD/output/qemu-x86_64/target/bin/busybox ash" \
  PYTHONDONTWRITEBYTECODE=1 python3 tests/client/supervisor-test.py
git diff --check
```

O BusyBox v1.38.0 é um binário histórico já existente, apenas executado para testar o shell; não foi recompilado. O supervisor inicia um processo Python simulado, não a aplicação Qt.

| Fonte exercitada | SHA-256 |
| --- | --- |
| `scripts/elo_content.py` | `1a82daced53106266bf9e88986fc7f8e0fd4dc9cd0a6c0c05516600affd25798` |
| `board/elo/qemu-gui/rootfs-overlay/usr/bin/elo-client-supervisor` | `26dbc3fd87c333ae37ac630c624e87d5682c0df98664ac793e2ebbde7a672617` |

Os cinco hashes dos artefatos históricos Pi 5/x86_64/ARM64 foram novamente comparados às referências P1 e permanecem iguais. Não houve nova execução de boot de console nesta entrega.

## Comportamento coberto

Ativação: tamanho/hash incorretos, JSON inválido, limites UTF-8 e NUL, falta de espaço injetada, releitura de bytes staged corrompidos, falhas antes/depois dos renames, reativação explícita, repetição, reutilização de bundle corrompido, caminhos inválidos/symlinks e leitores concorrentes observando um bundle completo anterior ou novo. Falha posterior à publicação é reportada como durabilidade incerta, com leitura de reconciliação; não é rollback fictício.

Supervisão: parada limpa sem filho órfão, exclusão de segundo supervisor no mesmo diretório, SIGKILL, SIGSTOP com PID ainda existente, timestamp fresco sem avanço de frames, geração incorreta, backoff/orçamento de reinícios e apresentação de erro responsiva sem convertê-la em READY_LOCAL. O teste com BusyBox encontrou um bloqueio no builtin `read` de procfs durante parada por sinal; o supervisor foi ajustado para leitura por comando externo e a bateria foi repetida. O ensaio BusyBox usa também seus applets cat/chmod/flock/mkdir/mv/rm/sleep existentes.

## Pendências de execução

Novos testes C++/Qt foram escritos para o ledger, diagnóstico, conteúdo externo, conectividade, retry e geração de saúde por frames. Ainda não foram compilados/executados nesta revisão. Nenhuma captura, medição de RAM ou biblioteca Qt carregada foi produzida para o código novo.

Os cenários QEMU sem NIC e com queda/reconexão de link, SIGKILL/SIGSTOP e shutdown estão implementados no runner, mas permanecem NOT TESTED nas duas arquiteturas. A fonte 202ab1d conserva sua [evidência histórica](P2-CLIENT-20261108.md), sem validar automaticamente essas mudanças.

Ativação usa filesystem descartável, não `/data`; falhas são injetadas, não cortes reais de energia. Eventos são modelo em memória, sem fila durável nem servidor. O perfil físico e os artefatos históricos não recebem estas mudanças.

Reprodução e próxima prova: [roteiro do desktop](../tests/desktop-validation.md), [contratos locais](../client/local-contracts.md), [matriz](../tests/acceptance.md).
