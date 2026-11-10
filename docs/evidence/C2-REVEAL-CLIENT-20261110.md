# C2 — Interação local Revelar — 2026-11-10

Escopo: Fedora host, cliente Qt nativo, servidor HTTPS e painel local. Sem validação
Buildroot/Pi 5. Nenhuma alteração no catálogo editorial ou seleção operacional.

- `cmake --build build/client-fedora --parallel 2`: PASS.
- CTest offscreen/software: 2/2 contratos PASS, incluindo teste Qt com clique,
  teclado, ocultação de imagem, revelação e reset; núcleo cobre navegação e rede.
- `./tests/smoke.sh`: PASS, 55 casos Python mais verificações estáticas.
- `python3 tests/network/distribution-test.py`: 15/15 PASS. Novo caso verifica
  recusa de cliente sem reveal-v3, download HTTPS, frame oculto e reinício offline.
- Importação de `var_cardeal_reveal_01` real: PASS, formato local 3, projeção
  `c5d40b7b88b01f0f252a8713c82e88ada86938c8e4e7df4d33a5b763e68661bc`.
- Serviço `elo-content.service` reinstalado com código atualizado, mantendo seleção.
- Chromium/Playwright no portal HTTPS: variante reveal habilitada, etiqueta
  “Toque para revelar” visível. Teste não publicou seleção.

Teste Qt aguarda estabilização do layout antes de coordenadas de clique. Primeiro
ensaio clicou antes do polish de Column/Flow e falhou; após sincronização, contrato
completo passou. Não foi necessário alterar comportamento do produto para esse caso.

[Contrato e uso](../client/reveal-interaction.md).
