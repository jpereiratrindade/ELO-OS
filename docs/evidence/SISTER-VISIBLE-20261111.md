# Interfaces Sister-Studio → ELO Studio — 2026-11-11

## Motivação

O usuário não encontrou mudanças nas interfaces dos dois Studios. Os incrementos
anteriores tinham implementado infraestrutura e correção de publicação, sem um
caminho de integração visível. Esta etapa acrescenta um percurso manual concreto.

## Disponível e instalado

- Sister-Studio Composição: painel e botão **Exportar composição para ELO**;
  histórico com **Exportar para ELO**; formulário de título, versão, licença,
  titular e revisão. Backend C++20 lê o render escolhido, valida PCM/limites,
  calcula SHA-256 e gera `.elo.json`. Sem nova persistência ou envio de rede.
- Voz/Vídeo: atalho **Composições → ELO**, identificando o escopo instrumental.
- ELO Studio: aba **Produções Sister-Studio** e botão superior **Receber do
  Sister-Studio**. Importação por sessão administrativa, lista de submissões,
  direitos/versão/duração/estado e reprodução privada do áudio revalidado.
- Recepção habilitada com credencial exclusiva e identidade `sister-studio-local`.
  O token não é disponibilizado nas interfaces ou encaminhado ao Sister-Studio.
- Frontend ELO usa identificador de versão no URL do script; recarga normal busca
  a versão nova. Backend serve apenas caminhos estáticos conhecidos, ignorando
  query de versão para esses arquivos.

Endereços da instalação verificados:

- Composição: `http://10.163.80.176:18013/`.
- ELO Studio: `https://10.163.80.176:8443/studio/`.
- Atalho no módulo Voz, `https://10.163.80.176:18043/`.
- Atalho no módulo Vídeo, `http://10.163.80.176:18014/`.

## Verificação executada

- Build C++ `sister_audio`, CTest e `apps/audio/scripts/run_quality.sh`: aprovados,
  incluindo hash MIDI canônico e validadores de contratos/governança.
- `scripts/validate_workspace.py` do Sister-Studio: aprovado.
- `tests/network/sister-export-import-test.py`: aprovado com os binários e rotas
  reais em instâncias temporárias. Composição de 5 segundos, exportação com Unicode
  e aspas, validação do manifesto/PCM, importação administrativa, repetição
  idempotente e comparação dos bytes de áudio. Campos inválidos/duplicados recusados.
- `tests/network/ingest-test.py`: nove testes aprovados, incluindo importação manual,
  recusa de tokens de terminal/produtor nessa rota e prévia privada.
- `tests/network/studio-intake-browser-test.py`: Firefox headless aprovou a aba e o
  atalho superior, seleção real de arquivo via DOM, envio do formulário, exibição
  da quarentena e criação do player com áudio autenticado. Um primeiro ensaio
  identificou falta de fallback para `submitter` nulo em submissão programática;
  corrigido, e o ensaio subsequente passou.
- `tests/smoke.sh`: aprovado com os novos testes de API e regressões existentes.
- Interfaces/JS servidos conferidos por HTTP/HTTPS; consulta administrativa da
  recepção instalada respondeu sem expor credenciais.

## Implantação e preservação

Biblioteca ELO completa preparada em diretório temporário e verificada antes da
troca, incluindo projeção da publicação existente e importação dos módulos.
Mantidos backup da biblioteca em `lib.before-sister-ui-20261111` e da unidade
systemd em `build/`. Serviço de conteúdo reiniciado com os argumentos dedicados
de ingestão. Backend editorial, banco e publicações do usuário não foram alterados.

Reiniciado somente o módulo Composição para carregar o C++ novo. O módulo Vídeo
foi reiniciado para recarregar o template, após conferir renderização em estado
`idle`. Arquivos do workspace preservados. Voz recebeu somente HTML/JavaScript
estáticos; inferência não foi reiniciada.

## Limites explícitos

Este é um fluxo de **exportar arquivo → importar arquivo**. Não há publicação
direta/outbound ou sincronização automática entre os Studios. O perfil aceita
somente composições instrumentais curtas. A recepção termina em quarentena e não
cria catálogo canônico, átomo, aplicação ou ativação. A revisão/catalogação ELO e
o uso editorial continuam pendentes. Não foram inseridos exemplos na instalação
nem publicados rascunhos do usuário. Testes não homologam hardware Pi.
