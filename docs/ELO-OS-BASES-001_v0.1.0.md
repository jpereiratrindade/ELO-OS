---
document_id: ELO-OS-BASES-001
title: "ELO/OS — Bases constitutivas e arquitetura de um Linux mínimo para o ELO Thin Client"
version: 0.1.0
status: design-candidate
date: 2026-11-08
authors:
  - "José Pedro Pereira Trindade — direção conceitual"
  - "ChatGPT — elaboração técnica colaborativa"
system: ELO/OS
target: "Raspberry Pi 5 / aarch64"
relationship:
  - "ELO-CONSTITUTION-001 v0.2.0"
  - "ELO Server — realização proposta"
  - "ELO Thin Client — realização proposta"
motto:
  - "Faça simples. Depois deixe mais leve."
  - "Sempre pronto. Sempre incompleto."
---

# ELO/OS — Bases constitutivas e arquitetura de um Linux mínimo

> **Faça simples. Depois deixe mais leve.**  
> **Sempre pronto. Sempre incompleto.**

**Documento:** ELO-OS-BASES-001  
**Versão:** 0.1.0  
**Estado:** *design-candidate* — decisões propostas, ainda não comprovadas em hardware  
**Data:** 08 de novembro de 2026  
**Plataforma de referência:** Raspberry Pi 5 (ARM64)  
**Artefato-alvo:** imagem Linux inicializável para operação como *appliance* de apresentação ELO

---

## 0. Declaração

O **ELO/OS** é uma realização Linux embarcada para dispositivos cuja função principal é executar o **ELO Thin Client**.

Ele não pretende desenvolver um novo kernel, substituí-lo, criar uma distribuição geral nem transformar o Raspberry Pi em um computador pessoal com desktop. Seu objetivo é **compor o menor sistema verificável que inicia, apresenta, se recupera e continua funcionando**.

A questão que orienta toda decisão é:

> **Este componente aumenta uma capacidade necessária do terminal ou apenas aumenta o sistema?**

Se não for necessário, não entra.

### 0.1. O que construiremos

Uma **distribuição-appliance** formada por kernel Linux, firmware adequado ao Raspberry Pi 5, *root filesystem* mínimo, inicialização e serviços essenciais, pilha gráfica, runtime de apresentação ELO, comunicação autenticada, cache local e mecanismos explícitos de recuperação.

### 0.2. O que não construiremos

Não desenvolveremos kernel, gerenciador de janelas próprio, protocolo proprietário sem necessidade, navegador completo, motor de banco de dados, sistema de atualização autoral nem interface gráfica de administração generalista.

**Minimalismo é redução de dependências e estados de falha, não ausência de mecanismos essenciais.**

---

## 1. Relação com a constituição do ELO

O ELO existente é um sistema independente, *offline-first*, com domínio de experiências, identidade e regras próprias. Seu documento de referência é **ELO-CONSTITUTION-001 v0.2.0**.

O ELO/OS **não revoga** essas definições. Em particular:

1. `ELO != Raspberry Pi`; o hardware não constitui sua identidade.
2. `ELO != ENTE` e `ELO != JEV`; dependências não se confundem com domínio.
3. A rede não pode ser condição para **toda** experiência local.
4. Apresentação/QML permanece separada do domínio e da persistência.
5. Privacidade, consentimento e separação de identidades continuam válidos.
6. A separação ELO Server / ELO Client é um **novo perfil de implantação a validar**, não uma reescrita silenciosa da constituição.

**Limite deliberado:** o terminal leve pode executar apenas o subconjunto de capacidades adequado a esse perfil. A autonomia local exigida por cada experiência precisa ser declarada; não se pode alegar compatibilidade integral com a constituição antes dos ensaios correspondentes.

### 1.1. Três entidades, três ciclos de vida

| Componente | Responsabilidade | Não deve assumir |
|---|---|---|
| **ELO Server** | Publicar versões e conteúdos; coordenar dispositivos; administrar distribuições; tratar funções centrais autorizadas | Controlar cada quadro de vídeo ou exigir conexão contínua para todas as experiências |
| **ELO Thin Client** | Interpretar manifestos, gerir cache e sessões locais, apresentar experiências, registrar eventos permitidos | Reimplementar o domínio completo do servidor ou inferir identidades sem política explícita |
| **ELO/OS** | Inicializar hardware, isolar serviços, disponibilizar rede/tela/entrada/armazenamento e recuperar falhas | Tornar-se gestor de conteúdo, motor de personalização ou autoridade sobre pessoas |

**ELO/OS ≠ ELO Thin Client ≠ ELO Server.**

---

## 2. Decisão arquitetural principal — ADR-001

**Decisão:** construir o ELO/OS com **Buildroot**, derivando inicialmente do `raspberrypi5_defconfig` oficial e mantendo as personalizações em árvore `br2-external`.

**Fundamento:** Buildroot compõe toolchain, kernel, pacotes e imagem mínima para um equipamento com função bem definida, sem exigir uma distribuição Linux de propósito geral.

| Alternativa | Vantagem | Limitação | Destino |
|---|---|---|---|
| Raspberry Pi OS Lite 64-bit | Prototipagem rápida; suporte de hardware conhecido | Imagem e manutenção maiores | **Bancada P0** |
| Buildroot | Composição controlada; imagem enxuta; firmware/aplicação no mesmo processo de build | Requer integração e disciplina de atualização | **Base do ELO/OS** |
| Yocto/OpenEmbedded | Gestão avançada de produtos e variantes | Custo de entrada e manutenção acima do necessário agora | Reavaliar apenas com exigência demonstrada |
| Linux From Scratch | Excelente para aprender internals | Manutenção e reprodutibilidade inadequadas ao dispositivo operacional | Apenas estudo |
| Kernel próprio | Controle extremo | Anos de trabalho para pouco benefício ao ELO | Rejeitado |

**Nota:** Buildroot não é um gerenciador de pacotes no dispositivo. A unidade de entrega será uma **imagem de sistema** versionada.

---

## 3. Arquitetura em uma visão

```text
                 REPOSITÓRIO / CI
                        |
                  Buildroot + ELO/OS
                        |
                imagem versionada
                        |
     +----------------------------------------+
     | Raspberry Pi 5 — ELO/OS                |
     |                                        |
     | EEPROM/firmware -> Linux -> init        |
     |                      |                 |
     |              dispositivos/rede          |
     |                      |                 |
     |            DRM/KMS + Mesa/EGL           |
     |                      |                 |
     |             Qt 6 / QML (EGLFS)          |
     |                      |                 |
     |                 ELO Client              |
     |                  /     \               |
     |          cache local   fila local       |
     |                  \     /               |
     |               /data (RW)               |
     |                                        |
     |       rootfs fixo (somente leitura)     |
     +-----------------+----------------------+
                       |
              HTTPS autenticado
                       |
               ELO Server (Linux)
              C++26 / headless
```

O cliente recebe **dados e conteúdo**, não uma transmissão contínua do desktop do servidor. A renderização principal ocorre localmente.

**Consequência:** o terminal é *thin* em **responsabilidades e administração**, mas preserva processamento suficiente para experiência e operação desconectada. Ele não é um *dumb terminal*.

---

## 4. Como o sistema operacional efetivamente começa

Sequência de referência do Raspberry Pi 5:

```text
energia
  -> ROM e bootloader em EEPROM SPI
  -> seleção de mídia/partição e arquivos de boot
  -> firmware/Device Tree + kernel Linux ARM64
  -> montagem do root filesystem
  -> processo PID 1 (init)
  -> dispositivos e permissões
  -> montagem de /data, /run e /tmp
  -> rede (sem bloquear a apresentação)
  -> inicialização da pilha DRM/KMS
  -> elo-client em tela cheia
  -> READY_LOCAL
  -> sincronização com ELO Server quando disponível
```

O kernel controla memória, processos, escalonamento, I/O, drivers e isolamento básico. O `init` inicia e supervisiona o espaço de usuário. A aplicação ELO é **um processo** rodando sobre essas camadas, não parte do kernel.

### 4.1. Os sete elementos que estudaremos na prática

| Elemento | Pergunta fundamental | Experimento |
|---|---|---|
| Bootloader | Como o hardware encontra o sistema? | Observar a cadeia de boot e as partições |
| Kernel | Quem gerencia CPU, RAM, GPU e drivers? | Inspecionar `/proc`, `/sys` e `dmesg` |
| Init / PID 1 | Quem inicia os serviços e recupera processos? | Derrubar o `elo-client` e observar retorno |
| Filesystem | O que deve ser persistente? | Reiniciar após gravação e simular energia interrompida |
| Rede | Como dois sistemas se encontram e se autenticam? | Desconectar e reconectar o cabo |
| Interface gráfica | Como a aplicação controla a tela sem desktop? | Qt EGLFS sobre DRM/KMS |
| Atualização | Como trocar versões sem perder uma unidade? | Testar reversão com imagem anterior |

---

## 5. Pilha técnica mínima — ADR-002

| Camada | Escolha inicial | Justificativa |
|---|---|---|
| Arquitetura | `aarch64` / Raspberry Pi 5 | Hardware de referência |
| Sistema base | Buildroot, versão **fixada** | Imagem reprodutível |
| Kernel | Linux da configuração suportada pelo Buildroot para RPi5 | Não manter *fork* próprio |
| `init` | BusyBox init | Poucos serviços, baixo custo |
| Ferramentas de usuário | BusyBox | Utilitários essenciais |
| Biblioteca C | Escolha da toolchain fixada, inicialmente `glibc` se necessário ao Qt | Compatibilidade prevalece sobre economia prematura |
| Gráficos | DRM/KMS + Mesa (V3D/VC4 conforme configuração) + EGL/GBM | Aceleração pela pilha Linux |
| Apresentação | Qt 6 / QML / Qt Quick em **EGLFS** | Reusar a tecnologia do ELO |
| Código de cliente | C++26 **onde houver suporte validado** | Continuidade técnica, sem bloquear entrega |
| Transporte | HTTPS/TLS | Simplicidade e interoperabilidade |
| Dados persistentes | Arquivos imutáveis + SQLite local apenas quando necessário | Evitar banco e daemon desnecessários |
| Descoberta | Endpoint configurado primeiro; mDNS posteriormente | Discovery não é autenticação |
| Logs | Buffer em RAM + exportação sob demanda | Pouca escrita |
| Atualização do SO | Imagem integral controlada na fase inicial | Evitar atualização parcial frágil |

**Gatilho de compatibilidade:** se o compilador ARM64 da toolchain fixada não oferecer os recursos de C++26 de que o cliente realmente necessita, será adotado um perfil C++23 compatível **somente para o alvo**, com testes e decisão documentada. Qt não precisa ser compilado no mesmo padrão do código de aplicação.

**Pilha gráfica de contingência:** se EGLFS/DRM/KMS não funcionar corretamente com o conjunto específico de kernel + Mesa + Qt na Pi 5, testar **Weston mínimo + Qt Wayland**. Não adotar X11, GNOME ou KDE por padrão. Isto é uma condição experimental, não uma garantia de compatibilidade já demonstrada.

---

## 6. Limites de software — ADR-003

### 6.1. Devemos incluir

- Kernel, firmware, Device Tree e módulos estritamente necessários.
- Acesso à tela HDMI e entrada por toque/USB conforme o equipamento real.
- Ethernet; Wi-Fi somente se o perfil de implantação o exigir.
- Pilha TLS com certificado/âncora confiável e sincronização de horário confiável.
- Runtime Qt necessário ao cliente e às mídias efetivamente usadas.
- Gerenciamento de estado local, logs limitados, recuperação do processo e identificador de dispositivo.

### 6.2. Não incluir no perfil v0.1

- Interface desktop e gerenciador de janelas tradicional.
- Chromium ou outro navegador como runtime obrigatório.
- Docker, Kubernetes, servidor SQL, daemon web de administração permanente.
- Python, compiladores, cabeçalhos de desenvolvimento e *debuggers* na imagem de produção.
- Bluetooth, câmeras, reconhecimento facial, microfone, codecs e aceleração de vídeo **sem caso de uso validado**.
- SSH aberto à rede por padrão.

**Atenção à constituição ELO:** a exclusão de câmeras e biometria nesta **primeira imagem mínima** significa que esta realização ainda não prova todas as capacidades de uma instalação ELO presencial. Capacidades de presença/continuidade poderão entrar em perfis específicos, obedecendo ao consentimento e à separação dos dados.

---

## 7. Armazenamento e tolerância a falhas — ADR-004

Objetivo: **preservar operacionalidade após desligamentos abruptos**, sem prometer que só a arquitetura de software resolve defeitos de energia ou mídia.

### 7.1. Layout lógico inicial

```text
/boot          arquivos de inicialização; escrita controlada
/              rootfs mínimo; somente leitura
/run           tmpfs, estado transitório
/tmp           tmpfs, temporários
/var/log       tmpfs, logs com retenção limitada
/data          persistente; montado em leitura/escrita
/data/device   identidade, certificados e configuração provisionada
/data/content  bundles validados, conteúdos ativos e anteriores
/data/queue    eventos locais permitidos, pendentes de confirmação
/data/state    estado transacional mínimo
```

Na fase inicial, o layout físico poderá ser **boot + rootfs + data**, com `rootfs` somente leitura. Não adicionar particionamento A/B antes de validar a cadeia de boot e o mecanismo real de reversão.

**Não confundir:** `BR2_ROOTFS_OVERLAY`, usado pelo Buildroot para inserir arquivos na imagem durante a montagem, **não é** o `overlayfs` de tempo de execução. Não precisamos do segundo apenas para ter um `rootfs` somente leitura.

### 7.2. Regras de persistência

1. Escrita persistente somente em `/data`, com permissões restritas.
2. Baixar para arquivo temporário na mesma partição, validar, `fsync` quando aplicável e **renomear atomicamente**.
3. Fazer `fsync` do diretório quando necessário para durabilidade da publicação.
4. Nunca destruir o conteúdo ativo antes de validar e ativar o substituto.
5. Manter espaço reservado para atualização, recuperação e escrita transacional.
6. Limitar cache por cota e política determinística; não remover bundle ativo.
7. Não persistir frames de câmera ou dados sensíveis por conveniência técnica.

**Observação:** `rename()` permite troca atômica de nome no mesmo filesystem, mas não substitui sincronização em disco, nem fornece transação entre múltiplos arquivos. `SQLite` será usado nos pontos em que atomicidade transacional for realmente necessária.

### 7.3. Hardware é parte da confiabilidade

Adotar alimentação recomendada para Pi 5 (**fonte USB-C oficial de 27 W ou equivalente devidamente validada**, conforme periféricos), refrigeração e mídia adequada. Para operação contínua, avaliar NVMe/SSD em vez de depender exclusivamente de microSD. Testar falha real de energia sob carga.

---

## 8. Inicialização, estados e recuperação — ADR-005

O `elo-client` deve começar **sem esperar a rede**. Sem servidor, inicia a última experiência local válida ou uma apresentação básica de disponibilidade.

### 8.1. Estados observáveis

```text
BOOTING
   |
   v
READY_LOCAL <--------------------------+
   |                                   |
   +--> CONNECTING --> ONLINE          |
   |                      |            |
   |                      v            |
   +<--------------- DEGRADED_OFFLINE  |
   |                                   |
   +--> UPDATE_STAGED --> VALIDATING --+
   |
   +--> ERROR_RECOVERABLE --> RESTARTING --> READY_LOCAL
   |
   +--> ERROR_FATAL --> DIAGNOSTIC_SCREEN
```

Estados são **do equipamento**, não estados epistemológicos do ELO e nem avaliações de pessoas.

### 8.2. Supervisão mínima

- `BusyBox init` como PID 1.
- Processo de lançamento com política explícita de reinício e *backoff* para evitar *crash loop* agressivo.
- Watchdog de hardware **somente após teste da cadeia completa de alimentação do watchdog**, incluindo limites e forma de alimentá-lo; nunca habilitar reinício cego apenas por ausência de rede.
- Não reiniciar a máquina por falha recuperável de conteúdo ou indisponibilidade do servidor.
- Tela diagnóstica simples, mas não divulgar segredos, tokens ou dados pessoais.

**Separar:** processo vivo ≠ interface útil. Um contador de vida precisa refletir progresso observável no ciclo de apresentação, não apenas um PID existente.

---

## 9. Relação com o ELO Server — ADR-006

O contrato inicial é de **distribuição seletiva de conteúdo e eventos**, não de acesso remoto a um desktop.

### 9.1. Fluxo mínimo

```text
1. Cliente inicia com seus dados e conteúdo locais
2. Cliente descobre endpoint pré-configurado
3. Cliente valida identidade/autenticidade do servidor
4. Cliente informa versão/capacidades estritamente necessárias
5. Servidor publica manifesto compatível
6. Cliente verifica versão, hashes e espaço disponível
7. Cliente recebe somente bundles ausentes ou modificados
8. Cliente valida, ativa e preserva possibilidade de voltar ao anterior
9. Cliente apresenta conteúdo local
10. Cliente envia eventos permitidos e aguarda ACK
```

### 9.2. Contrato HTTP mínimo *proposto*

| Método / rota ilustrativa | Propósito | Regra |
|---|---|---|
| `GET /v1/client/manifest` | Consultar manifesto do dispositivo/perfil | `ETag` e `If-None-Match` |
| `GET /v1/content/{sha256}` | Buscar artefato imutável | Hash esperado; download retomável após validação de faixa |
| `POST /v1/client/hello` | Negociação de capacidade e versão | Sem identidade de pessoa |
| `POST /v1/client/events` | Entrega de eventos permitidos | Chaves idempotentes; ACK explícito |
| `POST /v1/client/health` | Diagnóstico mínimo | Sem segredos, imagens ou dados pessoais |

**Estas rotas são propostas, não endpoints comprovadamente implementados no ELO atual.** O contrato definitivo exige acordo entre os dois novos projetos.

### 9.3. Propriedades do manifesto

- `schema_version`, `manifest_id`, `revision`, `min_client_version`.
- Identificador de artefato, tamanho em bytes, SHA-256, tipo de mídia, compatibilidade.
- Ordem declarada de ativação e estado anterior para reversão.
- Política explícita de validade e operação offline.
- Assinatura digital do manifesto **na etapa de endurecimento**, com formato canônico especificado (por exemplo CBOR canônico) e chaves provisionadas.

No perfil inicial, TLS autenticado protege o transporte e SHA-256 verifica os bytes recebidos segundo o manifesto confiado. **Hash não equivale a assinatura independente**, e certificado TLS não constitui *secure boot*.

### 9.4. Idempotência

Toda tentativa reenviável de evento deve carregar chave estável, identidade do equipamento, tipo, número de sequência/tempo lógico quando aplicável e versão de esquema.

```text
mesma chave + mesmo conteúdo => mesmo resultado lógico
mesma chave + conteúdo divergente => conflito explícito
falha após envio e antes do ACK => reenvio seguro
```

O servidor mantém deduplicação durável; o cliente mantém a fila até confirmação. **Entrega pode ser ao menos uma vez; efeito lógico deve ser idempotente.**

---

## 10. Modelo de confiança e privacidade — ADR-007

1. A descoberta mDNS, quando usada, fornece **candidatos de endereço**, jamais identidade confiável.
2. O cliente aceita somente um servidor autenticado por TLS contra CA própria ou chave pública fixada/provisionada. Não desabilitar validação TLS.
3. Credenciais do dispositivo são individuais e revogáveis; não embutir um segredo compartilhado na imagem pública.
4. Identidade de **dispositivo** nunca é intercambiável com identidade de **pessoa**, **ELO** ou **ENTE**.
5. Armazenamento de eventos locais segue minimização, prazo de retenção e regra de esquecimento compatíveis com o domínio.
6. A hora precisa ser confiável para uso normal de certificados: considerar RTC com bateria, horário persistido com limites e sincronização segura. Não aceitar certificados inválidos para contornar relógio não inicializado.
7. SSH só para perfil de desenvolvimento ou manutenção, com chave e rede limitada. Em produção, desabilitado por padrão.
8. Não afirmar inicialização segura verificada (*secure boot*) nem antirrollback de firmware sem implementar/verificar a cadeia de confiança completa para a Raspberry Pi 5.

**Princípio de fronteira:** o ELO/OS pode transportar e guardar informação autorizada; não deve descobrir, inferir ou fabricar identidades humanas por conta própria.

---

## 11. Atualizações: três caminhos distintos — ADR-008

**A. Conteúdo** — manifesto e bundles imutáveis; atualização frequente e reversível sem reboot. **Entra na v0.1.**

**B. Aplicação** — binário/runtime ELO Thin Client; atualização como imagem de sistema na fase inicial para evitar combinação não testada de ABI e bibliotecas. **Entra após a primeira imagem reproduzível.**

**C. Sistema operacional** — kernel, firmware, init, bibliotecas. **Não usar `apt upgrade` num dispositivo Buildroot**; publicar imagem completa e ensaiar atualização recuperável.

**Evolução proposta (v0.2+):** investigar RAUC + slots A/B + política de saúde/confirmar/reverter, **somente depois de validar** sua integração ao método de boot específico da Pi 5. A mera presença de duas partições não cria rollback automático.

---

## 12. Repositório independente e árvore proposta

**Nome sugerido de projeto:** `ELO-OS`  
**Relação:** repositório próprio, não *fork* do ELO atual nem subdiretório do ELO Server.

```text
ELO-OS/
├── README.md
├── VERSION
├── CHANGELOG.md
├── docs/
│   ├── ELO-OS-BASES-001_v0.1.0.md
│   ├── adr/
│   │   ├── ADR-001-buildroot.md
│   │   ├── ADR-002-graphics.md
│   │   └── ADR-003-storage.md
│   └── tests/
│       └── acceptance.md
├── external.desc           # obrigatório em br2-external
├── external.mk             # obrigatório em br2-external
├── Config.in               # obrigatório em br2-external
├── configs/
│   └── elo_pi5_defconfig
├── board/
│   └── elo/
│       └── pi5/
│           ├── rootfs-overlay/
│           ├── genimage.cfg
│           ├── post-build.sh
│           └── post-image.sh
├── package/
│   └── elo-client/
│       ├── Config.in
│       └── elo-client.mk
├── scripts/
│   ├── build.sh
│   ├── inspect-image.sh
│   └── check-device.sh
└── tests/
    ├── boot/
    ├── network/
    ├── offline/
    ├── recovery/
    └── security/
```

**Importante:** esta árvore define os artefatos a implementar. **Ela não foi gerada nem compilada neste documento.** `genimage.cfg`, receitas Buildroot e serviços de inicialização só serão considerados válidos após integração e ensaio.

---

## 13. Trilha operacional — do primeiro boot ao equipamento

### P0 — conhecer o hardware antes de reduzi-lo

Em **Raspberry Pi OS Lite 64-bit**, validar:

- Alimentação, armazenamento, Ethernet, HDMI/touch e refrigeração.
- GPU/DRM/KMS e apresentação Qt 6 em tela cheia **sem ambiente desktop**.
- Aplicação mínima em C++ com QML.
- Arranque automático e continuidade após desconexão de rede.

**Saída:** comprovar compatibilidade gráfica e conjunto real de dependências.

### P1 — nascer o Linux mínimo

Buildroot possui configuração oficial do Pi 5. Em uma **tag estável fixada** no repositório Buildroot, executar inicialmente:

```bash
make raspberrypi5_defconfig
make
ls -lh output/images/
```

A documentação do Buildroot indica a geração de `output/images/sdcard.img` para a configuração suportada.

**Não gravar a imagem em disco antes de confirmar o dispositivo de destino**: ferramentas como `dd` sobrescrevem a mídia especificada. A customização da imagem vem **depois do primeiro boot conhecido**, via `br2-external`, sem editar indiscriminadamente a árvore original do Buildroot.

**Saída:** imagem Pi 5 inicializável, console serial/HDMI funcional, base inventariada.

### P2 — mostrar algo na tela

Adicionar dependências mínimas Qt 6 + DRM/KMS + Mesa, compilar o `elo-client` para ARM64, executar o primeiro QML em tela cheia e testar toque/entrada.

**Saída:** interface visível a cada boot, sem login ou desktop.

### P3 — torná-lo ELO

Adicionar configuração individual do dispositivo, conteúdo local, sincronização via HTTPS, cache atômico, estados offline e telemetria mínima.

**Saída:** um servidor publica; o terminal recebe, valida e apresenta; a experiência continua sem rede.

### P4 — endurecer

Rootfs RO, segredos provisionados, usuário sem privilégio, limites de processos e escrita, watchdog testado, recuperação após queda de energia, assinatura de atualização e política de manutenção.

**Saída:** aparelho operável repetidamente, não apenas uma demonstração.

### P5 — atualizar sem perder equipamento

Só após as etapas anteriores, implementar e homologar A/B ou outra solução de recuperação verificável.

**Saída:** atualização malsucedida não implica reinstalação manual rotineira.

---

## 14. Metas de engenharia e medidas

**Metas provisórias**, não resultados já alcançados:

| Propriedade | Meta inicial de bancada | Como medir |
|---|---|---|
| Boot até primeira tela local | ≤ 25 s, p95 | 30 partidas frias |
| Recuperação de `elo-client` | ≤ 10 s, p95 | Injetar falha no processo |
| Continuidade sem servidor | ≥ 72 h para bundle autossuficiente válido | Desligar a rede e executar roteiro |
| Uso de RAM em repouso | ≤ 400 MiB para SO + app-base, excluindo cache de mídia variável | `/proc`, `smem` ou equivalente |
| Escrita ociosa persistente | Idealmente zero fora de eventos necessários | Medição por bloco/dispositivo |
| Rede indisponível | Não impedir interface e experiência local | Boot sem cabo e sem Wi-Fi |
| Idempotência de eventos | 0 efeitos duplicados para reenvios iguais | Falhas induzidas antes/depois do ACK |
| Instalação | Imagem reproduzível a partir de versões fixadas | Build repetido, metadados e hashes |
| Privacidade | 0 frames biométricos persistidos por padrão | Inspeção do armazenamento |

Esses valores deverão ser **mantidos, apertados ou revisados com justificativa** a partir dos testes em hardware. Não ocultar regressões usando médias convenientes.

### 14.1. Critérios de aceitação do primeiro marco

- [ ] Pi 5 inicia 30 vezes sem intervenção.
- [ ] HDMI exibe interface sem desktop.
- [ ] Cliente começa e apresenta offline.
- [ ] Morte do processo provoca recuperação limitada e observável.
- [ ] Servidor indisponível não provoca reboot em ciclo.
- [ ] Download interrompido não altera conteúdo ativo.
- [ ] Bundle íntegro substitui versão anterior de forma controlada.
- [ ] Reenvio do mesmo evento não duplica efeito lógico no servidor.
- [ ] Identidades de equipamento e pessoa permanecem separadas.
- [ ] Retorno após queda de energia foi ensaiado, com relatório.
- [ ] Componentes, licenças e versões da imagem são inventariados.
- [ ] Nenhuma senha/segredo comum é incorporado na imagem distribuível.

---

## 15. Questões técnicas deliberadamente abertas

| Questão | Hipótese inicial | Experimento que decide |
|---|---|---|
| Qt EGLFS funciona bem com Pi 5 e Buildroot selecionados? | Provável, mas precisa de ensaio integrado | Testar EGL/GBM, resolução, toque e vídeo |
| O cliente precisa de câmeras no perfil v0.1? | Não para a primeira imagem; sim possivelmente para perfis ELO presenciais | Casos de uso + constituição |
| C++26 efetivo na toolchain ARM64? | Suporte dependente de compilador e recursos utilizados | `try_compile`, CI e teste nativo |
| Conteúdo audiovisual exige GStreamer/FFmpeg? | Só para formatos comprovadamente necessários | Matriz real de mídia e codecs |
| SSD/NVMe substitui microSD no produto final? | Preferível para operação intensiva, condicionado ao perfil | Ensaios de estabilidade, consumo e falha |
| Servidor é único ou existem múltiplos? | Um endpoint confiável configurado na v0.1 | Testar descoberta e failover quando existir necessidade |
| A/B com RAUC é adequado ao boot da Pi 5? | Candidato, não decisão fechada | Protótipo de upgrade/rollback físico |
| Qual experiência funciona 72 h offline? | Bundle autossuficiente declarado | Teste de dependências e licenças |

**Regra:** nenhuma incerteza recebe uma pilha de software inteira como resposta automática.

---

## 16. Não objetivos e bloqueios

Não declarar o ELO/OS **pronto para produção** somente porque iniciou uma vez. Não publicar SSH aberto em redes de campo. Não expor interfaces de depuração ou dados pessoais. Não transferir biometria ao servidor como subproduto da sincronização. Não confundir rootfs somente leitura com ausência de risco de corrupção de `/data`. Não confundir *watchdog* com tolerância a energia defeituosa.

Qualquer mudança que degrade autonomia local, privacidade ou a separação de identidades exigirá análise explícita frente à constituição do ELO.

---

## 17. Definição de pronto / definição de incompleto

### Sempre pronto

Em cada marco, a versão deve ter **uma capacidade completa e demonstrável**, mesmo pequena: iniciar, mostrar, receber, armazenar, recuperar — uma por vez, sem simular implementação.

### Sempre incompleto

O sistema registra limites e testes não realizados, preservando interfaces abertas à evolução. *Incompleto* não é autorização para ser frágil; *pronto* não é alegação de perfeição.

### Faça simples. Depois deixe mais leve.

Primeiro medir e confirmar o caminho íntegro. Só depois reduzir pacotes, memória, boot, processos, frequência de escrita e tráfego — **sem retirar propriedades que mantêm o terminal utilizável**.

---

## 18. Governança, versionamento e continuidade documental

- Identificador documental persistente: `ELO-OS-BASES-001`.
- Versão deste texto: `v0.1.0`.
- Versão de imagem: `elo-os/<semver>+<build-id>`, vinculada a commit, configuração e hashes.
- Versão do cliente: independente da versão da imagem, porém com matriz explícita de compatibilidade.
- `0.1.x`: correções e esclarecimentos sem mudança de contrato.
- `0.x+1.0`: mudanças arquiteturais ou novas capacidades experimentais.
- `1.0.0`: apenas após critérios de aceitação e política de operação/atualização homologados.
- Cada alteração substantiva recebe ADR, consequência e teste de aceitação.
- A versão documental nunca deve ser confundida com uma imagem já compilada.

### Registro inicial de decisões

| ID | Decisão | Estado |
|---|---|---|
| ADR-001 | Buildroot + br2-external | Proposta |
| ADR-002 | Linux + BusyBox + Qt EGLFS / KMS | Proposta |
| ADR-003 | Inclusão mínima, por capacidade | Proposta |
| ADR-004 | Rootfs RO + `/data` persistente | Proposta |
| ADR-005 | Estados locais e recuperação supervisionada | Proposta |
| ADR-006 | Manifests/bundles via HTTPS e eventos idempotentes | Proposta |
| ADR-007 | Identidades separadas + TLS + privacidade | Proposta |
| ADR-008 | Atualização de conteúdo ≠ aplicação ≠ SO | Proposta |

---

## 19. Fontes e documentos associados

**Projeto de referência**
- ELO — repositório existente: https://github.com/jpereiratrindade/ELO
- Constituição ELO (v0.2.0): https://github.com/jpereiratrindade/ELO/blob/main/docs/constitution/ELO-CONSTITUTION-001.md

**Documentação técnica primária**, consultada em 08/11/2026:
- Buildroot — suporte oficial ao Raspberry Pi 5 (`raspberrypi5_defconfig`): https://github.com/buildroot/buildroot/blob/master/board/raspberrypi/readme.txt
- Buildroot — manual, init, overlays e `br2-external`: https://buildroot.org/downloads/manual/manual.html
- Qt 6 — Embedded Linux, EGLFS e DRM/KMS: https://doc.qt.io/qt-6/embedded-linux.html
- Raspberry Pi — documentação de hardware e alimentação: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- RAUC — documentação de integração: https://rauc.readthedocs.io/en/latest/integration.html

---

## 20. Síntese constitutiva

> **ELO/OS é o mínimo de sistema necessário para uma experiência ELO confiável em um equipamento embarcado.**
>
> Não precisa saber tudo o que o ELO sabe.  
> Precisa iniciar sempre que possível, mostrar o que foi validado, tolerar ausências, proteger o que guarda e recuperar-se de falhas previsíveis.
>
> **O servidor prepara. O cliente realiza. O sistema operacional sustenta.**
>
> **Simples. Leve. Sempre pronto. Sempre incompleto.**

---

## Histórico de versões

| Versão | Data | Alteração |
|---|---|---|
| `0.1.0` | 2026-11-08 | Definição inicial, decisões técnicas, fronteiras constitutivas, arquitetura, ensaios e marcos de implementação |

**Próximo marco documental sugerido:** `ELO-OS-IMPL-001_v0.1.0.md` — receitas reais Buildroot, configuração inicial ARM64, serviços de inicialização, pacote do cliente e imagem de bancada, com evidências de build e boot.
