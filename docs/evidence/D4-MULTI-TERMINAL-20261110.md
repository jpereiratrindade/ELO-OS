# D4 — Acompanhamento por totem — 2026-11-10

## Entrega

Portal MORFO acompanha nome, contato recente, última publicação/página apresentada,
posição, modo e duração por identidade. Cadastro administrativo emite token individual
uma única vez, guardando hash no servidor. Revogação bloqueia consultas e relatórios;
cache offline não é removido. Seleção editorial ainda é compartilhada.

Cliente envia dados de página após confirmação do frame correspondente. Painel consulta
a cada 5 s; heartbeat do cliente a cada aproximadamente 30 s. Sem contato por 90 s,
registro perde indicação de contato recente e mantém última apresentação conhecida.
Não transmite captura de tela, vídeo ou respostas do visitante.

## Verificação

- Build Qt nativo: PASS; CTest 2/2 PASS (33,71 s).
- `tests/network/distribution-test.py`: 18/18 PASS (26,38 s), incluindo dois clientes
  Qt reais com credenciais/caches separados e atualização automática de página no recibo.
- `tests/network/panel-test.py`: 11/11 PASS. Credenciais separadas, persistência,
  revogação, ausência de tokens em listagem e relatórios inválidos cobertos.
- Serviço PC instalado confirmou `Cardeal-amarelo`, página 1, em relatório schema 2.
  Também iniciou na sessão gráfica e confirmou conteúdo HTTPS/frames; serviço foi
  posteriormente parado, sem deixar override offscreen instalado.
- Chromium no portal LAN: cards separados PC/Pi, título real da apresentação, ausência
  de erros JS e validação de Origin da LAN. Download de credencial na UI testado com
  resposta simulada, sem criar cadastro fictício em produção.
- TLS validado por CA explícita e hostname, sem ignorar certificado, em localhost e
  10.163.80.176. Porta 8443 já estava permitida pela zona existente; firewall não alterado.
- Cadastro real **Raspberry Pi 5 · CPPSUL** criado; token privado fora do Git, incluído
  no roteiro local de provisionamento. Não enviou relatório fictício de Pi físico.
- Captura: `build/terminal-dashboard.png`. `git diff --check`: PASS.

Uma rodada de integração terminou com status 143; repetição completa passou.
Pi físico e caminho entre Wi-Fi de visitantes e rede cabeada continuam pendentes.

[Contrato e uso](../client/terminal-monitoring.md).
