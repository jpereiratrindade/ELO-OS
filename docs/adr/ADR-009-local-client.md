# ADR-009 — apresentação local e bancada gráfica virtual

**Status:** accepted para núcleo e apresentação experimental; integração gráfica por plataforma depende das evidências

**Data:** 2026-11-08

## Decisão

Desenvolver o cliente antes do ensaio físico P1-E, mantendo a ordem de validação por artefato. O núcleo em `package/elo-client/src/core/` usa somente a biblioteca padrão C++: começa em `BOOTING`, carrega e valida uma fixture incorporada identificada/versão 1, e só passa a `READY_LOCAL` após confirmação de apresentação. Oferece três páginas, navegação limitada e reinício da apresentação. Um catálogo injetável permite testar ausência, conteúdo inválido, incompatibilidade e timeout. Eventos tipados distinguem carga, frame apresentado, navegação e disponibilidade da rede; link disponível nunca estabelece `ONLINE`. Não espera rede nem cria arquivos. Esses estados descrevem a disponibilidade da apresentação local; não são identidade ou avaliação de uma pessoa, nem prova de prontidão do SO inteiro.

A tela é uma apresentação básica de disponibilidade, admitida pela seção 8 do documento-base. O conteúdo é demonstrativo, não um contrato de domínio ELO. Não criar endpoints, sessões pessoais ou sincronização fictícia. O frontend Qt observa o núcleo e encaminha ações. A confirmação vem de `frameSwapped` após carga da fixture, por conexão enfileirada; erro de carga ou apresentação não produz READY. O QML usa Qt Quick sem importar Controls, navegador ou serviços de rede.

A extensão local implementa portas com consumidores reais: store/catálogo de fixture JSON com tamanho/SHA-256, observador de link Linux, relógio monotônico, registro de frames e diagnóstico de transições. Um publicador Python de host testa ativação atômica de uma fixture em diretório descartável; não instala Python no alvo. A política idempotente é um modelo C++ em memória, sem transporte nem coleta de respostas. Detalhes e limites em [contratos locais](../client/local-contracts.md). Contratos C++23/Qt foram executados no desktop; resultados por arquitetura e método constam na [matriz de aceitação](../tests/acceptance.md). A evidência nativa histórica corresponde à fonte 202ab1d.

Substituir o C++17 do scaffold pelo perfil portátil C++23. O perfil `-DELO_CXX_STANDARD=26` é experimental, sem downgrade silencioso; aceitar a flag não comprova suporte completo de linguagem/biblioteca. Testar os recursos efetivamente usados com os compiladores reais. O núcleo usa `std::variant`/`std::visit`, strings e vetores, sem recursos novos de C++26; o mesmo contrato deve passar no host e no ARM64. A CI Ubuntu 24.04 usa C++23. CMake mínimo 3.25 para reconhecer o perfil 26. Isso não muda o padrão de compilação do próprio Qt.

Os perfis `qemu-x86_64-gui` e `qemu-aarch64-gui` têm defconfigs, overlays de identidade e diretórios de saída próprios. A bancada usa Qt Quick por software com LinuxFB/DRM e VirtIO GPU, sem Mesa, compositor ou desktop. Esta é uma escolha de teste portátil; EGLFS/V3D da Pi 5 permanece a proposta de ADR-002, sem promoção por este teste. A renderização por software é suportada pelo [Qt Quick](https://doc.qt.io/qt-6/qtquick-visualcanvas-adaptations.html); o modo LinuxFB DRM é descrito em [Qt for Embedded Linux](https://doc.qt.io/qt-6/embedded-linux.html).

## Limites

O `S50elo-client` pertence somente aos perfis gráficos virtuais. Inicia cliente e supervisor de bancada como root, com logs em `/run`. Saúde exige progresso de frames com geração/PID corretos; reinícios têm backoff e orçamento limitado. A lógica shell passou com processo simulado e Qt real no desktop; a integração das imagens x86_64/KVM e ARM64/TCG está registrada na matriz. Não estabelece política de produção ou recuperação de energia.

O lançador mantém snapshots descartáveis. O ensaio gráfico cobre partida sem NIC e cenário separado de perda/reconexão de link, além de SIGKILL/SIGSTOP e retorno à fixture inicial. Ambos passaram nas imagens x86_64/KVM e ARM64/TCG; a matriz identifica os artefatos verificados. Não há teste de 72 horas offline, disco `/data`, atualização do SO ou integração Pi 5 por associação.

Nenhum perfil de console aprovado ou artefato da Pi 5 recebe o cliente por esta mudança. Build, execução do núcleo ARM64, renderização Fedora, boot gráfico virtual e integração física têm evidências próprias.
