# ADR-010 — Manutenção remota no perfil pi5-client

Estado: implementado em 2026-11-10, após solicitação de operação sem mouse/teclado.

Perfil físico de cliente precisa de acesso administrativo independente da apresentação.
Falta de SSH impediu coleta remota de diagnóstico no primeiro ensaio físico; ausência de
sincronização de horário também foi identificada como lacuna para HTTPS.

`pi5-client` passa a incluir Dropbear, habilitado somente com chave pública provisionada
e sem autenticação por senha; chrony e referência local de horário; diagnóstico sem GUI.
Perfis base `pi5` e QEMU preservam sua política de não incluir SSH. Teste Kconfig exige
pacotes no cliente físico e continua proibindo-os nos demais perfis.

Não há bypass de TLS nem dependência de conectividade para apresentação local.
Chaves privadas de host são geradas por dispositivo, fora da imagem genérica. Chave
privada do administrador nunca é copiada. Serviço gráfico pode ser parado sem derrubar
SSH. IP e acesso entre redes continuam responsabilidade da configuração da instalação.

[Operação e ensaios](../client/remote-maintenance.md).
