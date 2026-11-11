# Premissas compartilhadas — aplicação de 2026-11-11

## Resultado

**Simples, leve. Sempre pronto. Sempre incompleto!**

- 166 projetos distintos receberam documentação e três símbolos SVG locais.
- 121 repositórios Git contêm commits das alterações desta tarefa.
- 78 remotos `origin` receberam os commits; os hashes foram conferidos com `git ls-remote`.
- 42 repositórios sem remoto configurado mantiveram seus commits locais.
- 45 projetos sem Git mantiveram os arquivos locais, por orientação do usuário.
- `Vulkan-Samples` tem commit local, mas seu `origin` pertence à KhronosGroup e recusou escrita com HTTP 403. Nenhum fork ou remoto foi criado.

O inventário cobre os projetos identificados em `/dev/cpp/` e também
`/dev/Sister-Studio`, que já fazia parte desta conversa. O diretório
`RESILIENCIA-RS-EXP001-v0.1.0` é um alias de `METIS` e não foi contado duas vezes.
Diretórios de build, caches e dados não foram tratados como projetos novos.

As alterações anteriores, sem relação com esta tarefa, foram preservadas na
árvore de trabalho e no índice. Os commits desta entrega incluem a integração
ELO/SYNTH e a identidade ELO criadas nesta conversa. Não se declara que todos
os repositórios estejam sem alterações anteriores.

## Aplicação visual

Cada projeto recebeu `docs/sister-principles/README.md`, os três SVGs e um
link no README principal. A pena representa simplicidade e leveza; o círculo
com confirmação, prontidão no escopo atual; o ciclo aberto, evolução contínua.
Os símbolos não representam saúde, identidade verificada ou validação científica.

As premissas foram incluídas nas 43 páginas de entrada HTML identificadas,
nas telas de login/navegação do Trama e no painel/Estúdio ELO. O cliente ELO-OS
recebeu o lema em seu rodapé. Projetos sem interface web receberam os artefatos
na documentação, sem alterações arbitrárias em seus motores ou interfaces nativas.

A verificação em navegador usou desktop de 1280 × 900 e celular de 390 × 844.
Os 43 blocos apresentaram três rótulos, ícones visíveis e ausência de
transbordamento. Scripts das aplicações foram desabilitados nessa inspeção:
é uma verificação de apresentação estática, não de seus fluxos autenticados.

## Verificações

- 26 testes Python do adaptador SisTer/SYNTH: passaram.
- 14 testes JavaScript de navegação: passaram.
- 3 testes CTest da base SYNTH: passaram no empacotamento oficial.
- 11 testes do painel ELO: passaram.
- 9 testes do provisionamento de terminais: passaram.
- Build TypeScript/Vite do Trama: passou.
- Cliente ELO-OS: compilação passou; 2 testes CTest de núcleo e interface passaram.
- SVGs validados como XML; diffs da tarefa conferidos antes dos commits.
- Erros de formatação encontrados em alterações anteriores não foram corrigidos como parte desta padronização.

## Instalações

O painel/Estúdio ELO e os atalhos desta máquina já receberam a identidade e
as premissas; o frontend instalado do LAC também foi atualizado. O cliente ELO
continua com a inicialização automática desabilitada.

O pacote oficial SisTer/SYNTH `principles-20261111`, construído a partir do
código commitado e com SHA-256 validado, foi enviado ao `labeco-srv`.
A release em execução ainda é `elo-20261111-01`; a ativação depende da senha
administrativa do servidor. Execute em um terminal interativo:

```bash
ssh -t jpereiratrindade@10.163.80.129 \
  'sudo bash ~/sister-elo-integration-20261111/activate.sh'
```

Não foram anunciadas como implantadas as demais interfaces que dependem de
instalação em outro host. Push Git não equivale a troca de release em execução.

## Commits e destinos

Os hashes abaixo identificam os commits de aplicação. O próprio relatório e
ajustes finais do cliente ELO-OS estão em um commit posterior no ELO-OS.
Branches de trabalho foram usadas nos dois checkouts destacados e na cópia
histórica SisterAppPEC_v411, cujo histórico diverge do remoto; não houve force push.

| Projeto | Commit | Branch de destino/local | Resultado |
| --- | --- | --- | --- |
| `Agent` | `df97825ea7` | `main` | Enviado e hash remoto conferido |
| `Beacon` | `ca95bd27f5` | `main` | Enviado e hash remoto conferido |
| `CONTINUUM` | `732f44f24c` | `main` | Enviado e hash remoto conferido |
| `CRIVO` | `2ec478123c` | `main` | Enviado e hash remoto conferido |
| `ContextLab` | `dbea0e4b97` | `main` | Enviado e hash remoto conferido |
| `DataBase` | `7797d77aee` | `master` | Commit local; sem remoto configurado |
| `DatabaseConnection` | `cf734552cf` | `master` | Commit local; sem remoto configurado |
| `ELO-OS` | `8de3811336` | `main` | Enviado e hash remoto conferido |
| `EcofunctionalPerceptron` | `eddbef416d` | `main` | Enviado e hash remoto conferido |
| `Ente` | `c9a55c920f` | `main` | Enviado e hash remoto conferido |
| `GeoHexBatch` | `8d5d714cd4` | `master` | Commit local; sem remoto configurado |
| `GeoHexBatchPsql` | `1df2cfa20b` | `master` | Commit local; sem remoto configurado |
| `GeoTiffReader` | `1d648d92d9` | `main` | Enviado e hash remoto conferido |
| `IdeaWalker` | `edf4603cb1` | `main` | Enviado e hash remoto conferido |
| `LCImage` | `2fb901cff6` | `master` | Enviado e hash remoto conferido |
| `LImagemProc` | `03fe8de472` | `master` | Commit local; sem remoto configurado |
| `LabGP` | `ee10bb4b2e` | `main` | Enviado e hash remoto conferido |
| `LabGestao` | `7e6b33b294` | `main` | Enviado e hash remoto conferido |
| `Labeco` | `3526a6e3cb` | `master` | Commit local; sem remoto configurado |
| `LabecoDesk-APIcppstd` | `8cf9e52b38` | `desenvolvimento` | Commit local; sem remoto configurado |
| `LabecoImage_n8nCli` | `26a3014fac` | `master` | Commit local; sem remoto configurado |
| `METIS` | `8bb51e4ca4` | `main` | Enviado e hash remoto conferido |
| `MIRANTE` | `e12b59e454` | `main` | Enviado e hash remoto conferido |
| `MORFO` | `c7d415944a` | `main` | Enviado e hash remoto conferido |
| `Multiv_VPillar_x64_Linux` | `46d3d9fd3c` | `main` | Enviado e hash remoto conferido |
| `NOESE` | `ccc5643ef7` | `main` | Enviado e hash remoto conferido |
| `OCAS` | `b6e1c4153a` | `main` | Enviado e hash remoto conferido |
| `PCTG` | `680da8dafe` | `main` | Commit local; sem remoto configurado |
| `PROBANTE` | `a8d5367617` | `main` | Enviado e hash remoto conferido |
| `PatchDynamics` | `86a25d9578` | `master` | Commit local; sem remoto configurado |
| `PatternIntegrityLab` | `62bbdc7a68` | `master` | Commit local; sem remoto configurado |
| `PatternIntegrityLab_v10` | `d63bc2cb83` | `master` | Commit local; sem remoto configurado |
| `Praxis` | `4ee630f368` | `integrate/praxis-lic-001-main` | Enviado e hash remoto conferido |
| `ProgEstrut` | `8fea8bed35` | `main` | Enviado e hash remoto conferido |
| `RIZOMA` | `1cbe99018d` | `main` | Enviado e hash remoto conferido |
| `SIGMA` | `f7fb26dbc9` | `main` | Enviado e hash remoto conferido |
| `SYNTH` | `88332f468c` | `main` | Enviado e hash remoto conferido |
| `SYNTH-0` | `8b27915922` | `main` | Enviado e hash remoto conferido |
| `SYNTH-WEB` | `58206d868c` | `main` | Enviado e hash remoto conferido |
| `SensDataAnalysis` | `db59fe3dce` | `master` | Enviado e hash remoto conferido |
| `SisAval` | `c4390bffb4` | `master` | Commit local; sem remoto configurado |
| `SisTer` | `bc4a8ac976` | `main` | Enviado e hash remoto conferido |
| `SisTer-Campo` | `91bf933ae7` | `master` | Commit local; sem remoto configurado |
| `SisTer-test` | `74c0a40db6` | `chore/shared-principles-20261111-sister-test` | Enviado e hash remoto conferido |
| `SisterAppEngine_base_v3225-beta-2` | `cf72ec02c7` | `refactor/unify-context` | Commit local; sem remoto configurado |
| `SisterAppEngine_base_v340` | `32655bc356` | `feature/terrain-slopes-v3.4.0` | Commit local; sem remoto configurado |
| `SisterAppEngine_base_v373` | `4007bd4932` | `feature/terrain-slopes-v3.4.0` | Commit local; sem remoto configurado |
| `SisterAppEngine_base_v379` | `48ea33a4f1` | `feature/terrain-slopes-v3.4.0` | Commit local; sem remoto configurado |
| `SisterAppEngine_base_v383` | `e1e16866d9` | `feature/terrain-slopes-v3.4.0` | Commit local; sem remoto configurado |
| `SisterAppEngine_base_v392` | `ebaa6c9e34` | `feature/terrain-slopes-v3.4.0` | Commit local; sem remoto configurado |
| `SisterAppEngine_v330-(base_v330)` | `5e29990ed8` | `master` | Commit local; sem remoto configurado |
| `SisterAppPEC` | `8a259b26e5` | `main` | Enviado e hash remoto conferido |
| `SisterAppPEC_v411` | `654ec17590` | `chore/shared-principles-20261111-sisterapppec-v411` | Enviado e hash remoto conferido |
| `SisterSTRATA` | `1e3e944b86` | `main` | Enviado e hash remoto conferido |
| `StreamParallel` | `e706017c34` | `master` | Commit local; sem remoto configurado |
| `TESSITURA` | `79e43f0b95` | `main` | Enviado e hash remoto conferido |
| `TRAMA` | `535a9d6cca` | `main` | Enviado e hash remoto conferido |
| `TRAMA-RS` | `bea4f3b35a` | `main` | Enviado e hash remoto conferido |
| `Teste_Rede` | `ac9dafc2ea` | `master` | Commit local; sem remoto configurado |
| `TinyKernel` | `48396c4548` | `main` | Enviado e hash remoto conferido |
| `TinyLogicLM` | `21bf735762` | `main` | Enviado e hash remoto conferido |
| `TinyLogicVision` | `0926780221` | `main` | Enviado e hash remoto conferido |
| `TinySystemOne` | `ef3eab73d7` | `main` | Enviado e hash remoto conferido |
| `VGAF` | `f22803e073` | `main` | Enviado e hash remoto conferido |
| `VGAF-Test` | `b4938467da` | `main` | Commit local; sem remoto configurado |
| `Vulkan-Samples` | `a2b5551ecf` | `main` | Somente local; remoto recusou escrita (403) |
| `cce` | `22257f07ef` | `main` | Enviado e hash remoto conferido |
| `cre` | `02cf888155` | `main` | Enviado e hash remoto conferido |
| `droneops` | `bc0f9bc086` | `main` | Enviado e hash remoto conferido |
| `elo` | `8a94b9b16e` | `main` | Enviado e hash remoto conferido |
| `ente-kernel` | `ac6606ea5e` | `main` | Enviado e hash remoto conferido |
| `evida` | `9b2a69ecc1` | `main` | Enviado e hash remoto conferido |
| `evida-reference` | `3656875d03` | `main` | Enviado e hash remoto conferido |
| `hello.c` | `bb156f4dbe` | `main` | Enviado e hash remoto conferido |
| `imagesDynamic` | `fb959c5d3e` | `main` | Enviado e hash remoto conferido |
| `labeco_SensRes_8s` | `23e6713773` | `main` | Enviado e hash remoto conferido |
| `lac-laboratorio` | `4bf0ad5486` | `main` | Enviado e hash remoto conferido |
| `libGeotifReader` | `b15897c9c7` | `main` | Enviado e hash remoto conferido |
| `libMLPerceptron` | `7a9848fd39` | `main` | Enviado e hash remoto conferido |
| `localchat` | `4f584032be` | `main` | Enviado e hash remoto conferido |
| `lume` | `801c54d6d0` | `main` | Enviado e hash remoto conferido |
| `macma` | `d58b58b4e4` | `master` | Commit local; sem remoto configurado |
| `morfocampo` | `5284ad5dca` | `master` | Enviado e hash remoto conferido |
| `n8nQtClient` | `ea88bee15f` | `master` | Commit local; sem remoto configurado |
| `nexo` | `d8eb505a3a` | `main` | Enviado e hash remoto conferido |
| `obce` | `1396746308` | `main` | Commit local; sem remoto configurado |
| `obce_gui` | `5429a902b9` | `main` | Commit local; sem remoto configurado |
| `procImage` | `1193f57f2e` | `main` | Enviado e hash remoto conferido |
| `radar_sister_resiliencia` | `b3ab4e09a1` | `main` | Enviado e hash remoto conferido |
| `radar_sister_resiliencia_old_em_git` | `dd3ac6e996` | `main` | Commit local; sem remoto configurado |
| `regsens` | `84f1e5d467` | `master` | Enviado e hash remoto conferido |
| `restaurars_api` | `22289f7015` | `main` | Enviado e hash remoto conferido |
| `sama-d_new` | `b0e656f17c` | `master` | Commit local; sem remoto configurado |
| `sama_d` | `4a96ca94e1` | `main` | Commit local; sem remoto configurado |
| `sinal` | `faca17c064` | `main` | Enviado e hash remoto conferido |
| `sinalcpp` | `3100b1bc8d` | `main` | Commit local; sem remoto configurado |
| `sister-atmos` | `6316e63242` | `main` | Enviado e hash remoto conferido |
| `sister-dsh-web` | `2039b5c0b4` | `main` | Commit local; sem remoto configurado |
| `sister-git` | `9ac8490f79` | `governance/pilot-rastreabilidade` | Enviado e hash remoto conferido |
| `sister-image` | `c5c74d9c62` | `main` | Enviado e hash remoto conferido |
| `sister-infra` | `9ef2287e49` | `main` | Enviado e hash remoto conferido |
| `sister-infra-atmos-lab-witness` | `09aeee13a5` | `chore/shared-principles-20261111-sister-infra-atmos-lab-witness` | Enviado e hash remoto conferido |
| `sister-kernel` | `df61d2a1a0` | `main` | Commit local; sem remoto configurado |
| `sister-memoria` | `cbaa6d8d69` | `main` | Enviado e hash remoto conferido |
| `sister-nexo` | `dc2632a355` | `main` | Enviado e hash remoto conferido |
| `sister-pcoa_v1.0` | `7188599930` | `master` | Commit local; sem remoto configurado |
| `sister-praxis` | `82efb56f32` | `main` | Enviado e hash remoto conferido |
| `sister-reflexa` | `a183bafa9c` | `main` | Enviado e hash remoto conferido |
| `sister-runtime-foundations` | `6a7d80999e` | `main` | Enviado e hash remoto conferido |
| `sister-sociotechnical-lab` | `037392ede3` | `main` | Commit local; sem remoto configurado |
| `sister-synth-poc` | `2c976ceb87` | `main` | Enviado e hash remoto conferido |
| `sister-urt` | `9472e3293b` | `master` | Enviado e hash remoto conferido |
| `sister_compras` | `ee212f4e2c` | `main` | Enviado e hash remoto conferido |
| `sisterd_lab` | `c9a0f22e31` | `main` | Enviado e hash remoto conferido |
| `teste` | `f9eec7565c` | `master` | Commit local; sem remoto configurado |
| `testeGTKMM40` | `f3464492d6` | `master` | Commit local; sem remoto configurado |
| `testeGTKmmDrawingArea` | `5eea30d3bd` | `master` | Commit local; sem remoto configurado |
| `teste_BoostHttp` | `80785d8960` | `master` | Commit local; sem remoto configurado |
| `teste_cUrl` | `0e1c23af63` | `master` | Commit local; sem remoto configurado |
| `testewxGTK` | `f34a876a68` | `master` | Commit local; sem remoto configurado |
| `Farina` | `` | `—` | Arquivos locais; sem Git |
| `LV-SSE` | `` | `—` | Arquivos locais; sem Git |
| `Labeco-ccp-web-v1.0` | `` | `—` | Arquivos locais; sem Git |
| `LabecoDA-1.0.4` | `` | `—` | Arquivos locais; sem Git |
| `RIZOMA-IMG-EXP-002-CPP26` | `` | `—` | Arquivos locais; sem Git |
| `RIZOMA-IMG-EXP-003-CPP26` | `` | `—` | Arquivos locais; sem Git |
| `RIZOMA-IMG-EXP-004-CPP26` | `` | `—` | Arquivos locais; sem Git |
| `Resiliencia` | `` | `—` | Arquivos locais; sem Git |
| `SisterAppEngine_base_v32` | `` | `—` | Arquivos locais; sem Git |
| `SisterAppEngine_base_v322` | `` | `—` | Arquivos locais; sem Git |
| `SisterAppEngine_base_v3222-beta` | `` | `—` | Arquivos locais; sem Git |
| `SisterAppEngine_base_v3223-beta` | `` | `—` | Arquivos locais; sem Git |
| `SisterAppEngine_base_v3224-beta` | `` | `—` | Arquivos locais; sem Git |
| `SisterAppEngine_base_v3225-beta` | `` | `—` | Arquivos locais; sem Git |
| `SoilSystem` | `` | `—` | Arquivos locais; sem Git |
| `SpecLab` | `` | `—` | Arquivos locais; sem Git |
| `TRACTUS` | `` | `—` | Arquivos locais; sem Git |
| `assistente` | `` | `—` | Arquivos locais; sem Git |
| `cpp_web_script_codex` | `` | `—` | Arquivos locais; sem Git |
| `farina` | `` | `—` | Arquivos locais; sem Git |
| `reference-subsystem` | `` | `—` | Arquivos locais; sem Git |
| `resiliencia-studio` | `` | `—` | Arquivos locais; sem Git |
| `sister-sindicato` | `` | `—` | Arquivos locais; sem Git |
| `sister_audio` | `` | `—` | Arquivos locais; sem Git |
| `sister_confia` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp-test` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp3D` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp3D-OpenGL` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp3D-Vulkan` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp3D-Vulkan (Cópia)` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp3D_v11` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp_mvp` | `` | `—` | Arquivos locais; sem Git |
| `sisterapp_webview` | `` | `—` | Arquivos locais; sem Git |
| `test_vulkcan_cpp` | `` | `—` | Arquivos locais; sem Git |
| `teste_newproj` | `` | `—` | Arquivos locais; sem Git |
| `vulkan` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base-v10` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base-v11` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base-v15` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base-v20` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base-v31` | `` | `—` | Arquivos locais; sem Git |
| `vulkan_base_v25` | `` | `—` | Arquivos locais; sem Git |
| `Sister-Studio` | `dbeb0e6021` | `main` | Enviado e hash remoto conferido |
| `Labeco-ccp-web` | `` | `—` | Arquivos locais; sem Git |
| `tkernel` | `` | `—` | Arquivos locais; sem Git |
