---
document_id: ELO-OS-IMPL-003
title: "Constituição operacional integral — desenvolvimento virtual"
version: 0.1.0
date: 2026-11-09
baseline_commit: 99ede0c
status: implementation-in-progress
software_version: 0.1.0
---

# ELO/OS — construção integral por capacidades verificáveis

Direção do mantenedor em 2026-11-09: adiar ensaios físicos e avançar a constituição integral do sistema. Não foi identificado contrato de distribuição Thin Client no ELO existente; o mantenedor acredita que ainda não o fizemos. Este plano organiza implementação e validação virtual sem converter essas pendências em resultados demonstrados.

Referências: [bases constitutivas](ELO-OS-BASES-001_v0.1.0.md), [P2](ELO-OS-IMPL-002_v0.1.0.md), [aceitação](tests/acceptance.md), [contratos locais](client/local-contracts.md). A constituição ELO disponível no checkout relacionado `../elo/docs/constitution/ELO-CONSTITUTION-001.md` permanece referência de domínio; esse repositório não é alterado por esta etapa.

## Fronteiras

- ELO/OS fornece boot, dispositivos, processos, armazenamento, rede e mecanismos de recuperação.
- Thin Client apresenta conteúdo autorizado e mantém seus próprios estados; a fixture atual continua sendo uma demonstração identificada.
- ELO Server publicará conteúdo e contratos autenticados. Painel administrativo existente no ELO não é presumido como esse servidor.
- Funcionalidade local não pode depender da existência do servidor.
- Identidades de equipamento, pessoa, ELO, ENTE e JEV permanecem separadas. Não acrescentar biometria, câmera ou dados pessoais para testar infraestrutura.
- A versão documental deste plano não constitui release do software nem homologação de um equipamento.

## Trilha integral

| Etapa | Entrega concreta | Prova exigida |
| --- | --- | --- |
| I0 — baseline | P2 já validado em Fedora, x86_64/KVM e ARM64/TCG | [Evidências P2](tests/acceptance.md), hashes e commit 99ede0c |
| I1 — fundação de appliance (PASS virtual) | Rootfs RO, temporários em RAM, disco `/data` independente, diagnóstico de falha e apresentação antes da rede | Dois perfis novos; escrita em `/` recusada; dados entre boots; SIGKILL da VM; ENOSPC; disco ausente/inválido; GUI e recuperação nas duas arquiteturas |
| I2 — identidade e isolamento | Provisionamento individual fora da imagem, identidade opaca de equipamento, cliente sem privilégios, permissões de dispositivos, limites de recursos e logs | Reinício preserva identidade; nenhum segredo comum; usuário/processos/dispositivos auditados; logs e escrita limitados; falhas de permissão explícitas |
| I3 — conteúdo e eventos duráveis | Ligar catálogo ao armazenamento persistente; ativação e reversão explícitas; reserva/cota; fila durável com ACK e reenvio limitado | Reinício após staging/ativação/ACK, corrupção, disco cheio, repetição/conflito e manutenção do último conteúdo válido; nenhuma dependência de servidor para apresentar |
| I4 — contrato e servidor real | Definir esquema/versionamento com o ELO; implementar servidor de distribuição e cliente TLS, autenticação de equipamento e relógio confiável | Integração real com certificados válidos; rejeitar servidor falso, certificado inválido e relógio inadequado; downloads interrompidos e respostas incompatíveis não alteram ativo |
| I5 — atualização e recuperação | Separar conteúdo de aplicação/SO; artefatos completos identificados, verificação antes da instalação e recuperação controlada | Imagem/bundle inválido recusado; perda de progresso não confirma atualização; reversão testada na plataforma virtual; boot Pi 5 e RAUC/A-B mantêm gate físico próprio |
| I6 — integração funcional ELO | Subconjunto de experiências realmente suportado pelo terminal, com negociação explícita de capacidades | Compatibilidade com domínio e conteúdos reais; ausência de capacidade resulta em rejeição explícita, sem fingir a totalidade da constituição ELO |
| I7 — operação e distribuição | Proveniência de imagem, inventário/licenças, manutenção, ensaios prolongados e métricas | Commit/configuração/dependências/hashes; teste de repetibilidade; limites de memória/escrita; 72 h offline; ciclos virtuais medidos; gates físicos continuam separados |

I2/I3 podem avançar sem integração com o servidor. I4 exige contrato implementado e testes de integração; as rotas ilustrativas das bases não são evidência de API existente. Assinaturas, boot verificado e antirrollback só recebem esses nomes quando a cadeia correspondente existir e for testada.

## I1 — fundação virtual implementada e verificada

Criados `qemu-x86_64-appliance` e `qemu-aarch64-appliance`, com defconfigs, identidades e saídas próprias. Os cinco perfis anteriores e seus artefatos foram preservados. Compartilhado somente o cache de fontes entre saídas, mantendo os caminhos absolutos das toolchains próprios de cada build.

Layout de execução:

```text
/                  ext4, montado somente leitura
/run               tmpfs, estado e diagnóstico transitórios
/tmp               tmpfs, temporários e logs transitórios
/var/lib           tmpfs, estado transitório dos serviços básicos
/var/log           symlink para armazenamento transitório do skeleton
/data              ext4 separado, rw,nosuid,nodev,noexec
  .elo-layout      ELO_DATA_V1
  device/          0700; reservado ao provisionamento posterior
  content/         0700; reservado à integração do catálogo
  queue/           0700; reservado à fila durável posterior
  state/           0700; estado local explícito
```

O launcher mantém snapshot do rootfs e conecta dados como um segundo arquivo de disco virtual gravável. `create-data-image.sh` cria somente um arquivo novo, publica sem substituir destinos existentes e nunca recebe dispositivo físico como alvo. Não há formatação automática no convidado.

`S35elo-data` reconhece somente o volume ext4 rotulado `ELO_DATA` em `/dev/vdb`. Cria diretórios privados e publica marcador após `fsync` do arquivo e diretório. Inicialização parcial pode ser retomada sem apagar estado existente; layout de versão desconhecida é recusado. Disco ausente, montagem/estrutura inválidas ou falha de sincronização produzem estado indisponível; não há armazenamento persistente alternativo na raiz.

Diagnóstico de boot em RAM:

```text
ELO_STORAGE_V1 INITIALIZING CHECKING_DEVICE
ELO_STORAGE_V1 READY MOUNTED
ELO_STORAGE_V1 UNAVAILABLE <motivo>
ELO_STORAGE_V1 STOPPED UNMOUNTED
```

O serviço de apresentação confirma frame/estado local antes de o script de rede iniciar. A falta de disco não impede a fixture incorporada, mas não é anunciada como prontidão de persistência. I1 não integra automaticamente conteúdo `/data` ao cliente nem implementa uma fila apenas por criar diretórios.

## Matriz de cobertura constitutiva

| Requisito das bases | Cobertura e etapa |
| --- | --- |
| Buildroot fixado, Linux/BusyBox, Qt sem desktop | I0 demonstrado; sete perfis após I1 |
| Autonomia, UI separada e conteúdo identificado | I0; integração de experiências reais em I6 |
| Boot sem esperar rede e recuperação por apresentação | I0 com supervisor; ordem de inicialização reforçada em I1 |
| Rootfs RO, escrita persistente restrita | I1; isolamento de usuário e cotas em I2/I3 |
| Preservar ativo, staging/validação/ativação sincronizados | Protótipo de host existente; integração persistente em I3 |
| Fila com chave estável, confirmação e idempotência | Modelo em memória existente; durabilidade I3 e deduplicação real de servidor I4 |
| Identidade individual e segredos provisionados | I2; confiança/TLS/relógio em I4 |
| Privacidade, retenção e esquecimento | Fronteiras já explícitas; mecanismos locais em I2/I3; regras de domínio ficam no ELO |
| Descoberta sem confundir endereço e identidade | Endpoint configurado e autenticado em I4; mDNS só com necessidade comprovada |
| Conteúdo/aplicação/SO com ciclos distintos | I3/I5; nenhuma alegação de A/B ou secure boot por simples particionamento |
| Métricas, logs, licenças, reprodução e manutenção | Evidência parcial I0; mecanismos I2/I7 |
| GPU, toque, energia, EEPROM, mídia e cadeia de boot Pi 5 | Adiados pelo mantenedor; nenhuma promoção por QEMU |

## Limites e segurança desta bancada

Appliance virtual é um perfil experimental. I1 ainda executa cliente como root e mantém console serial de desenvolvimento; I2 implementará isolamento e provisionamento. Rootfs montado RO protege contra escritas usuais, mas não equivale a dm-verity, secure boot ou proteção contra um administrador privilegiado.

O volume de dados pertence ao operador confiável. Rótulo e marcador de layout são verificações operacionais, sem autenticar autoria ou proteger contra adulteração física. Cache Qt e estado de serviços ficam em RAM; retenção segura do seed de entropia e horário persistente pertencem ao projeto de segurança posterior.

SIGKILL do QEMU depois de `fsync` testa interrupção do processo em virtualização, não perda real de energia, firmware ou mídia defeituosa. O host mantém seus próprios caches. Resultados são publicados com esse modelo de falha explícito.

## Aceitação e continuidade

I1 promovido no escopo virtual em 2026-11-09: [evidência](evidence/I1-APPLIANCE-20261109.md). Os dois builds terminaram e passaram nos cenários de rede com GUI e sem disco com apresentação viva, rootfs RO e arquivo de dados independente. Também passaram persistência após parada limpa e SIGKILL, inicialização parcial, staging não publicado, ENOSPC, layout desconhecido e disco sem formato/rótulo esperado. Logs, hashes e limitações foram registrados; as imagens base permaneceram inalteradas.

O [registro de aceitação](tests/acceptance.md) continua sendo fonte do estado demonstrado. A evidência registra seis cenários GUI, 16 boots de recuperação e hashes inalterados; I2–I7 permanecem pendentes, com proveniência inicial já presente em I1. As etapas seguintes recebem entregas/testes próprios; não declarar constituição integral implementada por concluir esta fundação. Testes físicos só serão retomados quando o mantenedor solicitar.
