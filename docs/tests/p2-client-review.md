# P2 — revisão do IMPL-002 e escopo desta entrega

Referência: [IMPL-002 v0.1.0](../ELO-OS-IMPL-002_v0.1.0.md), preservado sem alteração a pedido do mantenedor. O texto é um plano, não evidência de implementação nem autorização autônoma para executar cada comando. A entrega segue o pedido de núcleo portátil, interface Fedora, perfil gráfico separado e preparação ARM64. [ADR-009](../adr/ADR-009-local-client.md) registra decisões e limites.

## Consistência e adaptações

- Manter o núcleo em `package/elo-client/src/core/` permite um único pacote local Buildroot e um único CMake, com `ELO_BUILD_GUI=OFF` para não depender de Qt. A árvore `apps/` proposta no documento não é necessária nesta etapa. O núcleo continua lógica do Thin Client, não do kernel/SO.
- A fixture incorporada tem identidade, nome e versão 1, três páginas e limites estruturais de tamanho. O novo caminho externo é explicitamente opt-in, com tamanho/SHA-256, catálogo JSON e publicador atômico de host. Continua sendo conteúdo de teste, sem dados pessoais ou contrato de servidor; `/data` operacional permanece fora desta rodada.
- Eventos tipados cobrem carga, confirmação/falha de apresentação, navegação, retry e disponibilidade da rede. `READY_LOCAL` requer fixture válida e confirmação do adaptador. Qt confirma pelo frame renderizado, não pela mera existência do PID. Uma fixture inválida mantém erro explícito mesmo se a janela gerar frames.
- O teste unitário injeta ausência, incompatibilidade, corrupção estrutural, timeout reportado pelo catálogo e falha fatal. Isso não implementa timeout de I/O no núcleo. Eventos de rede não invocam sockets; o adaptador Linux observa link/endereço e encaminha eventos. Link disponível nunca promove `ONLINE`. O relógio injetado tem consumidores no ledger de teste e na saúde; os acréscimos C++/Qt aguardam compilação.
- Declarar os estados constitutivos não significa implementar protocolo, atualização ou recuperação de processo. Nesta etapa não há transições fictícias para ONLINE/UPDATE_STAGED/VALIDATING/RESTARTING.
- LinuxFB/DRM com buffers renderizados por CPU permite testar Qt Quick/VirtIO GPU sem Mesa/Weston. Weston adicionaria compositor e protocolo de janela sem requisito atual. A decisão não escolhe o backend gráfico da Pi 5.
- `S50elo-client` é exclusivo dos novos perfis gráficos de bancada. O supervisor implementa backoff, orçamento e saúde por avanço de frames; a lógica shell foi testada com processo simulado. Integração Qt real, imagens, falha/reinício e rede dinâmica ainda aguardam o desktop. Isso não promove P2-QGUI.
- O CMake faz `try_compile` do conjunto de biblioteca padrão usado (string/string_view/vector/variant/visit), no padrão selecionado. C++23 é o perfil principal; C++26 é experimento explícito. Aceitar `-std=c++26` não é prova de suporte completo ao padrão.
- O lançador existente ganhou modos opt-in; o caminho padrão dos perfis de console preserva máquina, discos, rede, console e snapshot. Como o código comum mudou, exigir regressão de boot, além de comparar hashes. Defconfigs P1 e artefatos não são recompilados.
- A afirmação de ausência de saída `fsck.fat` no documento histórico foi superada pela saída enviada pelo operador e por repetição local com código zero e hashes antes/depois; consulte [evidência Pi 5](../evidence/P1-BUILT-PI5-20261108.md).

## Mapa das tarefas

| Tarefa | Implementação / limite |
| --- | --- |
| T-200 | Artefatos históricos preservados; novos perfis gráficos isolados |
| T-201 | Núcleo C++ sem Qt/I/O implícito; validação anterior na fonte 202ab1d. Portas/diagnósticos novos aguardam recompilação |
| T-202 | Contrato offline anterior testado no núcleo; novos cenários GUI sem NIC e perda/reconexão de link aguardam desktop |
| T-203 | Portas explícitas com consumidores: catálogo, store, rede, relógio, apresentação e diagnósticos. Adaptadores C++/Qt novos ainda não compilados |
| T-204 | C++23 principal, try_compile, compiladores/bibliotecas e execução ARM64 registrados |
| T-205 | Conectividade, retry e catálogo externo acrescentados; novos testes Qt aguardam desktop |
| T-206 | Teste Qt e screenshot no Fedora; Xvfb e sessão gráfica real têm escopos distintos no relatório |
| T-207 | Dois perfis GUI; smoke cobre framebuffer, entrada, partida offline, queda/reconexão e SIGKILL/SIGSTOP. Build do laptop interrompido a pedido; ensaios NOT TESTED |
| T-208 | Compilação e execução do núcleo AArch64 em emulação de espaço de usuário; não é teste de GPU/kernel |
| T-209 | Protótipo de ativação atômica de host e testes Python implementados; consumidor Qt pendente de compilação. Não requer disco `/data` |
| T-210 | Modelo C++ em memória, conflito de chave/payload, reenvio limitado e ACK local; testes escritos, ainda não executados. Sem fila durável/servidor |
| T-211 | Supervisor shell testado no host com processo simulado; saúde Qt real e recuperação nas imagens NOT TESTED |
| T-212 | Q0 inclui testes host Python/shell; CI de compilação adiada nesta entrega pelo pedido de não compilar. Workflow permanece disponível |
| T-213 | Inspeção FAT repetida com código zero e hash preservado; boot físico permanece NOT TESTED |

A [matriz de aceitação](acceptance.md) e o relatório P2 associam cada resultado ao método e aos artefatos reais. Uma tarefa com extensão futura pendente não deve ser promovida por associação a outro teste.

A próxima compilação segue o [roteiro do desktop](desktop-validation.md). Os [contratos locais](../client/local-contracts.md) distinguem protótipo de ativação, ledger em memória e saúde de apresentação; código implementado não significa integração aprovada.
