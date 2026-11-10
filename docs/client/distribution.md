# Servidor de distribuição e cliente conectado

Acompanhamento atual por identidade e página: [Totens no servidor](terminal-monitoring.md).

Implementação experimental de distribuição textual, protocolo 1. Confirmação de recebimento e apresentação
está no [contrato de relatórios](delivery-receipts.md). O serviço lê
bundles publicados pelo ELO e gera a projeção textual já suportada pelo terminal.
A interface editorial continua no projeto ELO, agora acessível pelo
[painel integrado](server-panel.md). O endpoint do terminal não aceita uploads
nem operações administrativas. Credencial de terminal não concede acesso ao painel.

## Daemon instalado neste Fedora

Serviço do usuário: `elo-content.service`. Instalado e habilitado em 2026-11-10,
com HTTPS em `https://localhost:8443/v1/presentation`, escutando somente em
`127.0.0.1`. O usuário já possui `Linger=yes`, permitindo início sem login interativo.
Não foi alterada essa configuração. Não é acessível pela rede externa.

Origem configurada: `$HOME/.local/share/elo/content/current`, variante
`var_cardeal_ambient_01`. Publicações são relidas em cada requisição; trocar `current`
no ELO não exige reiniciar serviço, desde que a variante selecionada continue válida.

Para abrir cliente conectado, em sessão gráfica do Fedora, dentro de ELO-OS:

```bash
./scripts/run-thin-client.sh
```

O script compila a versão atual e usa cache independente em
`$HOME/.local/share/elo-client/content`. Não usa `build/elo-real-content` como origem.
Após primeiro download válido, reiniciar com servidor desligado mantém apresentação
local. Sem cache no primeiro uso, mostra falta de conteúdo até receber publicação
válida. Novas publicações são anunciadas e aplicadas ao Recomeçar/Home.

Gerenciamento:

```bash
systemctl --user status elo-content.service
journalctl --user -u elo-content.service -f
systemctl --user restart elo-content.service
systemctl --user stop elo-content.service
```

Instalação reproduzível ou atualização do código/configuração do serviço:

```bash
python3 scripts/install-content-service.py \
  --bundle "$HOME/.local/share/elo/content/current" \
  --variant var_cardeal_ambient_01
```

Instalador valida publicação, preserva credencial/certificado existentes, copia os
módulos Python e assets web para `$HOME/.local/share/elo-distribution/lib`, verifica unit,
habilita e reinicia daemon. Assim, código do serviço não depende da montagem do
checkout de desenvolvimento. Reexecutar instalador após alterar código do servidor.

Configuração privada em `$HOME/.config/elo-distribution/`:

- `terminal.token`: credencial aleatória individual desta bancada, arquivo 0600.
- `server.key`: chave privada local; nunca copiar para terminal remoto.
- `server.crt`: certificado local com SAN localhost/127.0.0.1, confiado explicitamente
  pelo cliente. Gerado por um ano; renovação ainda é operação do mantenedor.

Não incorporar esses arquivos em imagens nem no Git. Instalação atual usa um único
terminal/credencial. Cadastro, revogação por dispositivo, rotação automatizada e
atribuição de aplicações a múltiplos terminais ainda não existem.

## HTTPS em outra máquina

Serviço aceita `--host`, `--port`, `--cert` e `--key`; usar certificado válido para
nome do servidor. A instalação automática acima permanece limitada a localhost.
Exemplo de execução manual no servidor:

```bash
python3 scripts/elo_server.py --bundle /caminho/elo/content/current \
  --variant variante_textual --token-file /caminho/privado/terminal.token \
  --host 0.0.0.0 --port 8443 --cert /caminho/servidor.crt --key /caminho/servidor.key
```

No terminal provisionado, inicie cliente com caminhos absolutos:

```bash
./scripts/run-client.sh --server https://servidor:8443/v1/presentation \
  --content-dir /caminho/cache --token-file /caminho/terminal.token \
  --ca-file /caminho/ca.crt
```

O diretório pai do cache deve existir. Sem `--ca-file`, usa autoridades do sistema.
Certificado, hostname e validade temporal são verificados pelo TLS. Não há opção
para ignorar erros TLS. Para relógio incorreto, conexão falha e cache continua em uso;
esta etapa não implementa provisionamento de relógio confiável.

No launcher local, `ELO_SERVER_URL`, `ELO_CONTENT_DIR`, `ELO_CLIENT_TOKEN_FILE` e
`ELO_SERVER_CA_FILE` substituem padrões. Definir a última como string vazia usa CAs
do sistema. Certificado local atual cobre apenas localhost/127.0.0.1.

## Contrato de distribuição 1

`GET /v1/presentation`, cabeçalho `Authorization: Bearer <credencial>`; resposta
`application/json` com cinco campos:

```json
{
  "schema": 1,
  "sha256": "hash hexadecimal da apresentação UTF-8",
  "size": 123,
  "presentation": "JSON local serializado como string",
  "source": {
    "bundle_id": "aplicação original",
    "version": "versão editorial",
    "content_hash": "sha256:hash nativo ELO",
    "variants": ["variante selecionada"]
  }
}
```

`presentation` carrega bytes UTF-8 do catálogo local formato 1, sem mídia executável.
Servidor confere hash nativo de todo bundle e capacidades antes de responder. Origem
indisponível/adulterada/incompatível produz 503; credencial incorreta produz 401;
rota desconhecida produz 404. O servidor não altera conteúdo editorial.

Cliente exige HTTP 200, formato 1, tamanho/hash corretos e catálogo válido pelo
mesmo núcleo usado na apresentação. `source` é informativo; hash de apresentação
identifica o cache. A autenticidade de transporte depende de TLS e do provisionamento
confiável de CA/credencial, não do hash editorial isolado. Não há assinatura de bundle
ou proteção contra reativação de uma publicação antiga por servidor autorizado.

Requisições só começam após primeiro frame. Download é assíncrono, sem esperar rede
para apresentar cache. Timeout de inatividade: 10 s; prazo total: 15 s; resposta até
16 MiB e apresentação até 8 MiB. Sem redirects e sem proxy automático. Consulta a
cada 30 s; falhas repetem em 5/10/20/40/60 s, sem requisições concorrentes. O serviço
não mantém credencial em logs. Arquivo de token é relido em cada tentativa; falta ou
permissão inválida bloqueia download sem impedir uso do cache.

Cache usa mesmo lock de ativação do importador local; lock ocupado adia download.
Bundle é escrito e sincronizado antes da publicação atômica de `active.json`, seguida
por fsync do diretório. Nova publicação só recebe confirmação na UI após essas etapas.
Falha após publicar apontador, antes de fsync final, informa durabilidade inconclusiva
e repete reconciliação. Catálogo anterior permanece na memória da sessão.

Limites de escrita automática: até 32 diretórios de bundles, reserva de 4 MiB e até
quatro diretórios de download interrompido. Ao atingir limites, recusa publicação
nova; não apaga conteúdo automaticamente. Limites do importador manual são próprios.
Reativação idêntica não regrava apontador. Staging usa mesmo filesystem do cache.

## Aparência e fronteiras

Paleta do cliente segue `MORFO/web/style.css`, centralizada em
`package/elo-client/src/MorfoTheme.js`: fundo claro, superfície branca, azul-marinho,
azul/teal e foco dourado. Plus Jakarta Sans quando instalada; DejaVu Sans local como
alternativa. Não há download de fontes. Novas interfaces administrativas deverão
seguir essa mesma referência; o painel editorial do repositório ELO não foi alterado.

Esta entrega não completa I2/I3/I4/I6: identidade opaca persistente, isolamento do
processo, fila de eventos/ACK, capacidade multimídia, operação multi-terminal,
provisionamento e implantação no Pi 5 continuam pendentes. Serviço Python de
bancada usa biblioteca HTTP padrão, um processo e limites systemd; não representa
homologação de operação pública em produção.

## Verificação

```bash
./tests/smoke.sh
python3 tests/config-smoke.py
QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software \
  ctest --test-dir build/client-fedora --output-on-failure
PYTHONDONTWRITEBYTECODE=1 python3 tests/network/distribution-test.py -v
```

A integração requer cliente Qt compilado e `openssl`. Usa portas temporárias,
certificados/credenciais descartáveis e servidor real; não modifica daemon instalado.
Contrato Qt consultado: [QNetworkRequest 6.5](https://doc.qt.io/qt-6.5/qnetworkrequest.html).

[Evidência da implantação e testes](../evidence/D1-DISTRIBUTION-20261110.md).

Continuidade: [painel web e Estúdio editorial integrados](server-panel.md).

Evolução do cliente: [texto e imagem com cache offline](image-content.md).
