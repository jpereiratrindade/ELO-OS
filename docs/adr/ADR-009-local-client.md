# ADR-009 — apresentação local e bancada gráfica virtual

**Status:** accepted para núcleo e apresentação experimental; integração gráfica por plataforma depende das evidências

**Data:** 2026-11-08

## Decisão

Desenvolver o cliente antes do ensaio físico P1-E, mantendo a ordem de validação por artefato. O núcleo em `package/elo-client/src/core/` usa somente a biblioteca padrão C++: começa em `BOOTING`, carrega e valida uma fixture incorporada identificada/versão 1, e só passa a `READY_LOCAL` após confirmação de apresentação. Oferece três páginas, navegação limitada e reinício da apresentação. Um catálogo injetável permite testar ausência, conteúdo inválido, incompatibilidade e timeout. Eventos tipados distinguem carga, frame apresentado, navegação e disponibilidade da rede; link disponível nunca estabelece `ONLINE`. Não espera rede nem cria arquivos. Esses estados descrevem a disponibilidade da apresentação local; não são identidade ou avaliação de uma pessoa, nem prova de prontidão do SO inteiro.

A tela é uma apresentação básica de disponibilidade, admitida pela seção 8 do documento-base. O conteúdo é demonstrativo, não um contrato de domínio ELO. Não criar endpoints, sessões pessoais, cache ou sincronização fictícia. O frontend Qt observa o núcleo e encaminha ações. A confirmação vem do primeiro `frameSwapped` após carga da fixture, por conexão enfileirada; erro de carga ou apresentação não produz READY. A validação atual é estrutural da fixture incorporada, não validação SHA-256 de bundles externos. Os estados futuros são enumerados, mas não possuem transições de protocolo inventadas. Não acrescentar Qt Quick Controls, navegador ou serviços de rede.

Substituir o C++17 do scaffold pelo perfil portátil C++23. O perfil `-DELO_CXX_STANDARD=26` é experimental, sem downgrade silencioso; aceitar a flag não comprova suporte completo de linguagem/biblioteca. Testar os recursos efetivamente usados com os compiladores reais. O núcleo usa `std::variant`/`std::visit`, strings e vetores, sem recursos novos de C++26; o mesmo contrato deve passar no host e no ARM64. A CI Ubuntu 24.04 usa C++23. CMake mínimo 3.25 para reconhecer o perfil 26. Isso não muda o padrão de compilação do próprio Qt.

Os perfis `qemu-x86_64-gui` e `qemu-aarch64-gui` têm defconfigs, overlays de identidade e diretórios de saída próprios. A bancada usa Qt Quick por software com LinuxFB/DRM e VirtIO GPU, sem Mesa, compositor ou desktop. Esta é uma escolha de teste portátil; EGLFS/V3D da Pi 5 permanece a proposta de ADR-002, sem promoção por este teste. A renderização por software é suportada pelo [Qt Quick](https://doc.qt.io/qt-6/qtquick-visualcanvas-adaptations.html); o modo LinuxFB DRM é descrito em [Qt for Embedded Linux](https://doc.qt.io/qt-6/embedded-linux.html).

## Limites

O `S50elo-client` pertence somente aos perfis gráficos virtuais. Inicia um processo de bancada como root, sem supervisão, com logs em `/run`; não estabelece política de produção. O lançador mantém snapshots descartáveis. O ensaio gráfico remove a NIC virtual para comprovar inicialização local sem DHCP ou servidor. Isso não é teste de 72 horas offline, persistência, reconexão, atualização, recuperação ou energia.

Nenhum perfil de console aprovado ou artefato da Pi 5 recebe o cliente por esta mudança. Build, execução do núcleo ARM64, renderização Fedora, boot gráfico virtual e integração física têm evidências próprias.
