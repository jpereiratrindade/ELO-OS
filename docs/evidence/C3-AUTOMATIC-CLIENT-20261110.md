# C3 — Totem sem mouse — 2026-11-10

Fedora host, Qt nativo, servidor local HTTPS. Sem ensaio Buildroot/Pi 5.

- Build nativo: PASS.
- CTest com offscreen/software: 2/2 contratos PASS (33,53 s), incluindo exposição
  real de 5 s, espera por frame, preservação do prazo diante de frames/rede,
  controles ocultos, rolagem, navegação em ciclo e atualização no fim da sequência.
- Integração de distribuição: 16/16 PASS. Entrada automática a partir de cache
  manual, cliente antigo recusado, sessão mantida offline, HTTPS e reinício cobertos.
- Smoke: PASS, 56 casos Python mais verificações estáticas. Novo caso do painel
  cobre persistência, hash da duração, limites e retorno ao modo manual.
- Chromium/Playwright: modo automático publicado com 15 s na seleção operacional;
  variantes anteriores preservadas. Recarregamento confirma persistência.
  Captura local: `build/server-autoplay-panel.png`.
- Serviço `elo-content.service` atualizado.

Durante verificação, uma execução de integração coincidiu com relink do binário e
falhou ao iniciá-lo. Reexecutada após conclusão do build: 16/16 PASS. Teste Qt passou
a usar texto com espaços para verificar rolagem; seu limite CTest foi ampliado para
60 s para acomodar os prazos reais de exposição adicionados (não tempo de produção).

[Uso e contrato](../client/automatic-playback.md).
