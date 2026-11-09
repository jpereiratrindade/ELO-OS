# ADR-004 — Persistência isolada

**Status:** accepted no escopo virtual QEMU; proposed para Pi 5/produção

**Data:** 2026-11-08  
**Documento-base:** ELO-OS-BASES-001 v0.1.0

## Decisão

Usar rootfs somente leitura com `/data` independente nos perfis virtuais `qemu-x86_64-appliance` e `qemu-aarch64-appliance`. Manter temporários em RAM, volume ext4 explicitamente provisionado e recusa de disco/layout inválido, sem formatação automática ou fallback de persistência na raiz. A apresentação local inicia antes da rede e permanece disponível sem dados.

Não acrescentar partição à imagem física P1 nesta etapa. Os perfis de console e gráficos P2 anteriores preservam suas características.

## Consequências e limites

Implementação e revisão local verificadas nas duas arquiteturas: [evidência I1](../evidence/I1-APPLIANCE-20261109.md), [reprodução](../tests/appliance-validation.md). Persistência após SIGKILL do QEMU, ENOSPC e reinício limpo não equivalem a queda física de energia. Rótulo/layout não autenticam um volume; raiz RO não equivale a secure boot. Isolamento de usuário, catálogo/fila e atualizações continuam em etapas próprias.

Rollback de produção, mídia e energia dependem de ensaios próprios. Testes físicos foram adiados pelo mantenedor.

## Critério de promoção

O escopo virtual foi promovido após implementação, revisão e testes correspondentes. Promover a extensão Pi 5/produção somente com implementação e evidência específicas; resultados QEMU não promovem hardware.
