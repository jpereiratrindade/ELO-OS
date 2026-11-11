# Rede — testes futuros
- [ ] Boot sem Ethernet e sem Wi-Fi.
- [ ] DHCP apenas onde necessário; reconexão sem reinício.
- [ ] TLS com certificado válido e relógio confiável.
- [ ] Host falso/mDNS não consegue autenticar como servidor.

## Distribuição textual HTTPS

Com cliente Qt nativo compilado e `openssl` disponível:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tests/network/distribution-test.py -v
```

Usa servidor real com portas efêmeras e credenciais/certificados temporários.
Verifica autenticação, TLS/hostname, limites, integridade, interrupção, exclusão mútua,
retry e apresentação offline após reinício. Não altera daemon instalado.
[Contrato e operação](../../docs/client/distribution.md).
## Consumíveis Sister-Studio

`python3 tests/network/consumable-test.py` gera PCM WAV em diretório temporário e
verifica pré-validação somente leitura, identidade do manifesto, corrupção, duração,
direitos declarados, traversal, symlink, FIFO, arquivos extras e saída da CLI.
Também executado por `tests/smoke.sh`; não comprova ingestão HTTP ou gates G1–G9.
Consulte [o contrato inicial](../../docs/client/sister-consumables.md).

`python3 tests/network/ingest-test.py` testa HTTP/TLS real, credenciais separadas,
staging/commit/quarentena, idempotência concorrente, persistência após reabrir o
estado, conflitos, cotas, integridade e cliente CLI. Executado no smoke; requer
`openssl` para o certificado temporário. Sem catálogo editorial ou serviços instalados.

## Publicação de imagem pelo Studio

`node tests/network/studio-publishing-test.js` testa resolução de conflito de versão,
cancelamento, falha de validação e edição concorrente. Smoke executa quando Node
está disponível. O ensaio opcional com backend ELO compilado fica em:

```bash
python3 tests/network/studio-image-publish-test.py --elo-root ../elo
```

Cria workspace, SQLite, gateway e IPC isolados; faz upload de PNG, publica versão
nova pelo helper JavaScript real e confere cache e versão anterior. Não altera o
conteúdo instalado e não requer build de imagem ou cliente Qt gráfico.

## Exportação e recepção pelas interfaces

```bash
python3 tests/network/sister-export-import-test.py --sister-root ../../Sister-Studio
python3 tests/network/studio-intake-browser-test.py --elo-root ../elo
```

O primeiro usa o binário Sister-Studio C++ real em workspace temporário, gera e
exporta WAV e importa pelo gateway isolado. O segundo abre o frontend ELO real no
Firefox headless com sessão de teste e confirma aba, importação de arquivo, estado
de quarentena e player autenticado. Ambos são opcionais; não alteram projetos ou
serviços instalados. A API de importação manual e a prévia também integram o smoke.
