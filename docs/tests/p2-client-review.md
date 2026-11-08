# P2 — revisão do IMPL-002 e escopo desta entrega

Referência: [IMPL-002 v0.1.0](../ELO-OS-IMPL-002_v0.1.0.md), preservado sem alteração a pedido do mantenedor. O texto é um plano, não evidência de implementação nem autorização autônoma para executar cada comando. A entrega segue o pedido de núcleo portátil, interface Fedora, perfil gráfico separado e preparação ARM64. [ADR-009](../adr/ADR-009-local-client.md) registra decisões e limites.

## Consistência e adaptações

- Manter o núcleo em `package/elo-client/src/core/` permite um único pacote local Buildroot e um único CMake, com `ELO_BUILD_GUI=OFF` para não depender de Qt. A árvore `apps/` proposta no documento não é necessária nesta etapa. O núcleo continua lógica do Thin Client, não do kernel/SO.
- A fixture incorporada tem identidade, nome e versão 1, três páginas e limites estruturais de tamanho. É conteúdo de teste, sem dados pessoais. Não há bundle externo ou ativação persistente; validação de tamanho/SHA-256 de arquivos pertence a T-209.
- Eventos tipados cobrem carga, confirmação/falha de apresentação, navegação, retry e disponibilidade da rede. `READY_LOCAL` requer fixture válida e confirmação do adaptador. Qt confirma pelo frame renderizado, não pela mera existência do PID. Uma fixture inválida mantém erro explícito mesmo se a janela gerar frames.
- O teste unitário injeta ausência, incompatibilidade, corrupção estrutural, timeout reportado pelo catálogo e falha fatal. Isso não implementa timeout de I/O ou relógio real. Eventos de rede não invocam sockets; perda/reconexão preservam a página. Link disponível nunca promove `ONLINE`.
- Declarar os estados constitutivos não significa implementar protocolo, atualização ou recuperação de processo. Nesta etapa não há transições fictícias para ONLINE/UPDATE_STAGED/VALIDATING/RESTARTING.
- LinuxFB/DRM com buffers renderizados por CPU permite testar Qt Quick/VirtIO GPU sem Mesa/Weston. Weston adicionaria compositor e protocolo de janela sem requisito atual. A decisão não escolhe o backend gráfico da Pi 5.
- `S50elo-client` é exclusivo dos novos perfis gráficos de bancada, sem backoff/supervisão. O ensaio não deve promover o gate completo P2-QGUI do documento, que também pede falha/reinício supervisionado. Registrar separadamente boot/renderização/entrada/offline/shutdown quando efetivamente testados.
- O CMake faz `try_compile` do conjunto de biblioteca padrão usado (string/string_view/vector/variant/visit), no padrão selecionado. C++23 é o perfil principal; C++26 é experimento explícito. Aceitar `-std=c++26` não é prova de suporte completo ao padrão.
- O lançador existente ganhou modos opt-in; o caminho padrão dos perfis de console preserva máquina, discos, rede, console e snapshot. Como o código comum mudou, exigir regressão de boot, além de comparar hashes. Defconfigs P1 e artefatos não são recompilados.
- A afirmação de ausência de saída `fsck.fat` no documento histórico foi superada pela saída enviada pelo operador e por repetição local com código zero e hashes antes/depois; consulte [evidência Pi 5](../evidence/P1-BUILT-PI5-20261108.md).

## Mapa das tarefas

| Tarefa | Implementação / limite |
| --- | --- |
| T-200 | Artefatos históricos preservados; novos perfis gráficos isolados |
| T-201 | Núcleo C++ sem Qt/I/O implícito; biblioteca, controlador, eventos e testes |
| T-202 | Contrato offline e falhas injetadas no núcleo; ensaio GUI sem NIC tem evidência própria |
| T-203 | Parcial: catálogo e eventos de apresentação/rede. LocalStore/Clock/Diagnostics e transporte serão criados quando tiverem consumidores reais |
| T-204 | C++23 principal, try_compile, compiladores/bibliotecas e execução ARM64 registrados |
| T-205 | Modelo Qt, fixture identificada, estado observável, erro e entrada; sem protocolo |
| T-206 | Teste Qt e screenshot no Fedora; Xvfb e sessão gráfica real têm escopos distintos no relatório |
| T-207 | Dois perfis GUI e smoke de framebuffer/entrada/offline; resultado exige build e ensaio correspondentes |
| T-208 | Compilação e execução do núcleo AArch64 em emulação de espaço de usuário; não é teste de GPU/kernel |
| T-209 | Pendente: ativação persistente e falhas de filesystem, sem adicionar disco ou `/data` |
| T-210 | Pendente: especificação de fila/idempotência; não há contrato de servidor nesta entrega |
| T-211 | Pendente: supervisão, backoff, travamento e recuperação; PID e frame inicial não provam saúde contínua |
| T-212 | CI separa Q0, contrato C++ e teste Qt de host; nenhum desses jobs inicializa imagem ELO/OS |
| T-213 | Inspeção FAT repetida com código zero e hash preservado; boot físico permanece NOT TESTED |

A [matriz de aceitação](acceptance.md) e o relatório P2 associam cada resultado ao método e aos artefatos reais. Uma tarefa com extensão futura pendente não deve ser promovida por associação a outro teste.
