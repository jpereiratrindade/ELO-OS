# P2 — revisão do IMPL-002 e escopo desta entrega

Referência: [IMPL-002 v0.1.0](../ELO-OS-IMPL-002_v0.1.0.md), preservado sem alteração a pedido do mantenedor. O texto é um plano, não evidência de implementação nem autorização autônoma para executar cada comando. A entrega segue o pedido de núcleo portátil, interface Fedora, perfil gráfico separado e preparação ARM64. [ADR-009](../adr/ADR-009-local-client.md) registra decisões e limites.

Atualização de 2026-11-09: validação do desktop demonstrou contratos nativos C++23/Qt, sessão gráfica Fedora e imagens [x86_64/KVM](../evidence/P2-DESKTOP-X86-20261109.md) e [ARM64/TCG](../evidence/P2-DESKTOP-AARCH64-20261109.md), incluindo rede dinâmica e recuperação. Núcleo ARM64 passou em C++23 e no subconjunto experimental C++26.

## Consistência e adaptações

- Manter o núcleo em `package/elo-client/src/core/` permite um único pacote local Buildroot e um único CMake, com `ELO_BUILD_GUI=OFF` para não depender de Qt. A árvore `apps/` proposta no documento não é necessária nesta etapa. O núcleo continua lógica do Thin Client, não do kernel/SO.
- A fixture incorporada tem identidade, nome e versão 1, três páginas e limites estruturais de tamanho. O novo caminho externo é explicitamente opt-in, com tamanho/SHA-256, catálogo JSON e publicador atômico de host. Continua sendo conteúdo de teste, sem dados pessoais ou contrato de servidor; `/data` operacional permanece fora desta rodada.
- Eventos tipados cobrem carga, confirmação/falha de apresentação, navegação, retry e disponibilidade da rede. `READY_LOCAL` requer fixture válida e confirmação do adaptador. Qt confirma pelo frame renderizado, não pela mera existência do PID. Uma fixture inválida mantém erro explícito mesmo se a janela gerar frames.
- O teste unitário injeta ausência, incompatibilidade, corrupção estrutural, timeout reportado pelo catálogo e falha fatal. Isso não implementa timeout de I/O no núcleo. Eventos de rede não invocam sockets; o adaptador Linux observa link/endereço e encaminha eventos. Link disponível nunca promove `ONLINE`. O relógio injetado tem consumidores no ledger de teste e na saúde; os contratos C++23/Qt passaram no desktop.
- Declarar os estados constitutivos não significa implementar protocolo, atualização ou recuperação de processo. Nesta etapa não há transições fictícias para ONLINE/UPDATE_STAGED/VALIDATING/RESTARTING.
- LinuxFB/DRM com buffers renderizados por CPU permite testar Qt Quick/VirtIO GPU sem Mesa/Weston. Weston adicionaria compositor e protocolo de janela sem requisito atual. A decisão não escolhe o backend gráfico da Pi 5.
- `S50elo-client` é exclusivo dos perfis gráficos de bancada. O supervisor implementa backoff, orçamento e saúde por avanço de frames; a lógica shell foi testada com processo simulado e Qt real no host. Imagens x86_64/KVM e ARM64/TCG passaram com SIGKILL/SIGSTOP e rede dinâmica, fechando o gate P2-QGUI virtual para os artefatos registrados.
- O CMake faz `try_compile` do conjunto de biblioteca padrão usado (string/string_view/vector/variant/visit), no padrão selecionado. C++23 é o perfil principal; C++26 é experimento explícito. Aceitar `-std=c++26` não é prova de suporte completo ao padrão.
- O lançador existente ganhou modos opt-in; o caminho padrão dos perfis de console preserva máquina, discos, rede, console e snapshot. Como o código comum mudou, exigir regressão de boot, além de comparar hashes. Defconfigs P1 e artefatos não são recompilados.
- A afirmação de ausência de saída `fsck.fat` no documento histórico foi superada pela saída enviada pelo operador e por repetição local com código zero e hashes antes/depois; consulte [evidência Pi 5](../evidence/P1-BUILT-PI5-20261108.md).

## Mapa das tarefas

| Tarefa | Implementação / limite |
| --- | --- |
| T-200 | Artefatos históricos preservados; novos perfis gráficos isolados |
| T-201 | Núcleo C++ sem Qt/I/O implícito; portas/diagnósticos exercitados nos contratos nativo e ARM64 da fonte c456f0b |
| T-202 | Contrato offline nativo e cenários GUI x86_64/KVM e ARM64/TCG sem NIC e com perda/reconexão passaram |
| T-203 | Portas explícitas com consumidores: catálogo, store, rede, relógio, apresentação e diagnósticos. Contratos C++/Qt passaram no desktop |
| T-204 | C++23 principal, try_compile, compiladores/bibliotecas e execução ARM64 registrados |
| T-205 | Conectividade, retry e catálogo externo exercitados pelos testes Qt offscreen e na sessão gráfica xcb do desktop |
| T-206 | Teste Qt e screenshot no Fedora; Xvfb e sessão gráfica real têm escopos distintos no relatório |
| T-207 | Dois cenários por perfil, x86_64/KVM e ARM64/TCG, passaram com framebuffer/entrada, offline, queda/reconexão e SIGKILL/SIGSTOP |
| T-208 | Núcleo AArch64 da fonte c456f0b aprovado em QEMU user, C++23 e subconjunto experimental C++26; evidência gráfica separada |
| T-209 | Protótipo de ativação atômica e testes Python de host; consumidor Qt compilado/testado no desktop. Não requer disco `/data` |
| T-210 | Modelo C++ em memória, conflito de chave/payload, reenvio limitado e ACK local; contratos nativo e ARM64 passaram. Sem fila durável/servidor |
| T-211 | Supervisor com processo simulado e Qt real no host; saúde/recuperação demonstradas nas imagens x86_64/KVM e ARM64/TCG |
| T-212 | Q0 e contratos executados no desktop; compilação remota havia sido adiada na entrega do laptop. Workflow permanece disponível; novos resultados locais não são execução de CI |
| T-213 | Inspeção FAT repetida com código zero e hash preservado; boot físico permanece NOT TESTED |

A [matriz de aceitação](acceptance.md) e o relatório P2 associam cada resultado ao método e aos artefatos reais. Uma tarefa com extensão futura pendente não deve ser promovida por associação a outro teste.

Reprodução dos ensaios no [roteiro do desktop](desktop-validation.md). Os [contratos locais](../client/local-contracts.md) distinguem protótipo de ativação, ledger em memória e saúde de apresentação; os resultados se aplicam apenas aos métodos e artefatos registrados.
