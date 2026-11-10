# Distribuição textual HTTPS e daemon — 2026-11-10

PASS experimental no host Fedora x86_64. Base ELO/OS `c60dd89` mais alterações
locais desta entrega; contrato editorial do ELO consultado no checkout `93c00bd`.
Não promove I2/I3/I4/I6 integralmente.

## Operação real

Instalado e habilitado `elo-content.service` no systemd do usuário. Serviço ativo,
com restart em falha, MemoryMax 128 MiB, TasksMax 32, LimitNOFILE 128, filesystem
somente leitura no namespace do serviço, diretórios temporários privados e sem
novos privilégios. `systemd-analyze --user verify` passou. `Linger=yes` já estava
configurado; não foi alterado. Início após reboot não foi ensaiado nesta entrega.

Listener somente `127.0.0.1:8443`, HTTPS. Certificado local inclui localhost e
127.0.0.1, com confiança explícita no cliente. Credencial aleatória em arquivo 0600
fora do checkout. Endpoint não oferece upload nem acesso administrativo.

Bundle original lido de `$HOME/.local/share/elo/content/current`, aplicação
`app.elo.teste`, versão `0.1.0`, variante `var_cardeal_ambient_01`. Repositório ELO
e origem editorial não foram modificados.

Ensaio contra daemon instalado:

- Requisição sem credencial: HTTP 401.
- Requisição autenticada com confiança TLS explícita: HTTP 200, aplicação esperada.
- Cliente Qt iniciou com cache independente em `build/elo-server-content`.
- Download HTTPS, hash e estrutura validados, publicação local confirmada.
- Registro de saúde confirmou frame, estado pronto e digest exato do texto recebido.
- Processo de ensaio encerrado; daemon permaneceu ativo e habilitado.
- Log local: `build/elo-server-render.log`; nenhum token ou chave incluído no Git.

Launcher entregue: `scripts/run-thin-client.sh`, com cache operacional padrão em
`$HOME/.local/share/elo-client/content`, separado das demonstrações locais anteriores.

## Verificações

- Build nativo Qt concluído.
- `tests/network/distribution-test.py`: 10 testes passaram, 10,64 s. Exercitam
  serviço real e cliente Qt: HTTP local explicitamente habilitado, HTTPS confiado,
  certificado não confiável, hostname incorreto, credencial rejeitada/ausente,
  conteúdo adulterado, interrupção de download, formato/hash inválidos, resposta
  grande, redirect, lock ocupado, retry e reinício sem servidor com cache renderizado.
- CTest núcleo e Qt: 2/2 passaram, 8,56 s, incluindo troca de publicação pela UI.
- Smoke: 45 testes Python e checagens estáticas passaram.
- Kconfig dos oito perfis passou; cliente agora seleciona Qt Network, OpenSSL e CAs.
- `git diff --check` passou.

## Referência visual

Cliente passou a usar paleta de `MORFO/web/style.css`, centralizada em
`MorfoTheme.js`. Frame Qt inspecionado em `build/morfo-client.png`: fundo claro,
superfície branca, texto azul-marinho, ação azul, detalhe teal e foco dourado.
Fonte local alternativa, sem depender da rede. Painel administrativo ELO não alterado.

## Limites

Ensaio visual usa plataforma offscreen/software; não valida monitor ou Pi 5.
Nenhuma imagem Buildroot foi recompilada nesta entrega. Configuração Kconfig não é
prova de runtime TLS no ARM64. Não houve implantação pública, alteração de firewall,
ensaio de reboot ou abertura de portas para outras máquinas.

Publicação editorial e distribuição são componentes separados. Esta entrega cobre
texto selecionado e uma credencial de terminal; faltam painel integrado de upload,
provisionamento multi-terminal, rotação/revogação automatizadas, eventos duráveis e
ACK, isolamento do cliente e capacidades adicionais do domínio ELO. Cache preservado
em memória não garante recuperação de ponteiro adulterado depois de reiniciar.
