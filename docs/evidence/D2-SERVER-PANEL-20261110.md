# Painel de distribuição e Estúdio ELO — 2026-11-10

Implementado e implantado no Fedora do operador, sobre D1. Mesmo endereço HTTPS
local passa a servir interface, sem expor credencial de terminal ao navegador.

## Entrega e integração real

- `https://localhost:8443/`: landing/login e painel MORFO com publicação, seleção e prévia.
- `https://localhost:8443/studio/`: frontend ELO existente com paleta MORFO.
- Backend nativo existente iniciado por novo `elo-studio.service`, loopback 18080.
- Gateway autenticado `/api/*` compartilha workspace/editorial do ELO e mantém
  credencial administrativa separada da credencial de distribuição do terminal.
- Seleção de distribuição gravada atomicamente em estado separado; sem alterar
  átomos ou manifesto ELO ao selecionar variantes.
- Dois daemons ativos e habilitados. Não foi ensaiado reboot nesta etapa.

## Ensaios

Seis testes do painel passaram: landing, autorização separada, seleção persistente
com ordem refletida em resposta real do terminal, incompatibilidade, hash desatualizado,
Origin externo, proxy fixo e autorização de mídia. Dez testes anteriores de distribuição
passaram novamente após introdução do gateway.

Playwright/Chromium headless contra daemon HTTPS instalado: login usando credencial
local sem imprimi-la, catálogo e disponibilidade reais, prévia, confirmação da mesma
seleção já ativa e abertura do Estúdio. Catálogo `Teste de Aplicação` carregado.
Verificadas paleta MORFO e ocultação dos controles do antigo kiosk. Galeria de mídia
abriu. Capturas locais em `build/server-panel.png` e `build/server-studio.png`.
Nenhuma edição/publicação do conteúdo editorial original foi feita pelo ensaio de UI.

Upload nativo testado com instância separada do binário `elo-admin` em workspace
**descartável**, gateway HTTP em porta efêmera: POST `/api/upload`, PNG de 1 pixel,
resposta 200 e bytes persistidos idênticos. Confirmada ausência desse arquivo no
workspace original. Essa prova verifica encaminhamento e persistência; TLS do daemon
instalado foi exercitado separadamente no navegador e nos testes de distribuição.

O repositório ELO permaneceu limpo (`git status --short` sem alterações). Servidor
editorial abre SQLite/WAL e projeções existentes conforme funcionamento do ELO; não
foi criado um banco editorial concorrente no ELO/OS.

## Limites

Servidor segue local. Ainda não há operação multi-terminal, confirmação remota por
terminal ou suporte multimídia no cliente. Upload e editor já aceitam capacidades
que o terminal textual recusa. Página inicial informa esse limite. Backend existente
não foi recompilado nesta entrega; integração usa binário já disponível no checkout.
Aviso de certificado no navegador não foi removido por confiar globalmente na CA.
