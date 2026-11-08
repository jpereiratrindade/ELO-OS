# ADR-004 — Persistência isolada

**Status:** proposed  
**Data:** 2026-11-08  
**Documento-base:** ELO-OS-BASES-001 v0.1.0

## Decisão

Projetar rootfs somente leitura com /data; não implementar partição adicional na imagem P1.

## Consequências e limites

Rollback e queda de energia dependem de ensaios reais.

## Critério de promoção

Mudar para `accepted` somente com revisão de implementação e evidência de teste correspondente.
