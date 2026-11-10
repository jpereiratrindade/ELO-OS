# C5 — PC e Pi 5 provisionados — 2026-11-10

## Implementação

- Lançador compartilhado `elo-terminal`, sem interpretar configuração como shell.
- PC: cópia instalada do binário, supervisor, serviço de sessão gráfica, cache
  persistente. `elo-client.service` instalado e habilitado nesta bancada.
- Pi: serviço de boot condicionado a configuração, supervisor incluído no pacote,
  lançador linuxfb, cache persistente em `/var/lib/elo-client/content`.
- Provisionamento de raiz montada com Wi-Fi WPA2-Personal: senha em prompt oculto
  ou arquivo privado 0600. PSK derivada, SSID em hexadecimal, sem senha em argumentos.
- Pi exige conteúdo inicial automático válido; `consoleblank=0` no perfil atualizado.

## Ensaios executados

- Build nativo atualizado: PASS.
- Serviço PC instalado, iniciado via systemd com override temporário offscreen:
  frames Qt avançaram, cache manual recebeu programação automática de 15 s sem clique.
  Ao fim serviço parado e override removido; autostart permanece habilitado para sessão.
- `systemd-analyze --user verify` da unit instalada: PASS.
- Smoke: verificações estáticas e 62 casos Python PASS na rodada com seis testes de
  provisionamento. Depois foi acrescentado teste PTY: suíte de provisionamento 7/7 PASS.
- Teste PTY verifica senha digitada com eco desligado, ausência em saída capturada
  e arquivo final. Demais casos cobrem PSK, permissões, symlink de senha recusado,
  URL, preservação de cache, caminhos especiais, raiz Pi falsa e boot não provisionado.
- Kconfig: oito perfis PASS; não executa build ou boot.
- `git diff --check`: PASS.

## Limites

Sem build atualizado de imagem completa ou hardware Pi nesta rodada. Provisionamento
Pi foi testado em diretórios temporários, não em cartão. Servidor da bancada permanece
restrito a localhost; acesso LAN e certificado adequado precisam ser preparados antes
do ensaio Pi. PC e Pi compartilham modelo atual de um terminal e devem ser testados
alternadamente até suporte a múltiplas identidades.

[Instruções](../client/terminal-provisioning.md).
