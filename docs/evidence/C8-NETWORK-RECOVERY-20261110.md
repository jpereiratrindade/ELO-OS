# C8 — Recuperação de rede — 2026-11-10

## Observação física

Pi 5 com imagem C7 iniciou apresentação automaticamente. Após conexão por cabo,
obteve 10.163.80.128 e permitiu SSH com chave provisionada. `elo-network-probe`
retornou HTTP 200. Cliente mantinha erros de transporte; reinício somente da
apresentação restabeleceu publicação e recibos reais ao servidor. Wi-Fi estava
associado sem IPv4 no primeiro diagnóstico e depois obteve 10.163.4.249.

Essas observações não comprovam causa única de falha. Rede de visitantes e cabo
pertencem a sub-redes distintas; isolamento continua possível.

## Alteração

Cliente limpa cache de conexões após erro de transporte, antes da próxima requisição
com gerenciador livre. Não cancela publicação ou recibo em andamento e mantém cache,
verificação TLS, sequência e identidade do processo. DHCP Wi-Fi passa a solicitar
respostas broadcast, hostname e opções de busca/rotas; intervalo entre rodadas sem
concessão passa a três segundos. Serviço continua assíncrono.

## Artefato

`output/pi5-client/images/sdcard.img`, SHA-256:
`c8e97f72eb63bb07fbc7523826423a79219e35e80d12e68ac52462b42e379419`.

Manifesto e instalador local atualizados para esse hash. Imagem ainda não gravada
no cartão nem validada fisicamente nesta etapa.

## Verificação

Build nativo e Buildroot Pi-client: PASS. Smoke: PASS, 67 testes.
Distribuição: PASS, 20 testes, incluindo início offline com cache e conexão posterior
a servidor disponibilizado sem reiniciar processo.

Ensaio ARM64 de manutenção: PASS. Inclui perda deliberada da rota do servidor e restauração,
exigindo retomada de downloads e recibos no mesmo PID. Resultado final registrado em
`output/pi5-client/maintenance-qemu.json`. QEMU não valida rádio nem DHCP institucional.

## Ensaio físico após gravação

Nova imagem foi gravada e iniciou no Pi 5. SSH pelo cabo funcionou em
10.163.80.128; Wi-Fi recebeu 10.163.4.249; chrony confirmou sincronização NTP.
HTTPS retornou 200 e relatórios de apresentação chegaram ao servidor.

Após retirada do cabo, comunicação deixou de chegar ao servidor. Ao reconectar,
cliente retomou publicação sem reiniciar processo e aplicou seleção de uma página
“Campos Sulinos”, com cinco segundos de exposição. Recibo confirmou hashes recebido
e apresentado iguais. Usuário confirmou atualização funcionando pelo cabo.

Funcionamento exclusivo pelo Wi-Fi continua pendente de diagnóstico; concessão DHCP
e associação ao AP não comprovam acesso HTTPS estável ao servidor nessa rede.
