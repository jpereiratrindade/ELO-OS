# Manutenção remota do Pi 5

Perfil `pi5-client` agora inclui SSH Dropbear por chave pública, chrony para horário
e `elo-diagnose`. Apresentação, rede, relógio e SSH são serviços independentes.
Cliente continua mostrando cache enquanto rede ou horário ainda estão sendo ajustados.

## Provisionar antes de instalar cartão

Use instalador da bancada atualizado:

```bash
sudo ./output/pi5-client/instalar-microsd.sh
```

Roteiro local identifica leitor por serial, faz backup do layout anterior, confere hash
e bytes gravados e provisiona Wi-Fi, identidade individual, CA, cache automático,
chave pública SSH e referência inicial de horário. Solicita senha Wi-Fi sem eco.
Não envia senha ou chave privada ao Pi. Chave autorizada nesta bancada:
`~/.ssh/id_ed25519_labeco.pub`. Apenas parte pública é instalada em
`/root/.ssh/authorized_keys` com permissões 0600; diretório tem 0700.

Provisionamento manual de outra raiz montada também exige chave, por exemplo:

```bash
sudo python3 scripts/install-terminal.py --platform pi5 --root /mnt/elo-root \
  --server https://10.163.80.176:8443/v1/presentation \
  --token-file /caminho/pi5-terminal.token --ca-file /caminho/server.crt \
  --seed-content /caminho/cache-automatico --wifi-ssid CPPSUL-VISITANTES \
  --ssh-authorized-key /caminho/id_ed25519_labeco.pub
```

Chaves de host SSH são geradas no próprio aparelho e persistem em `/etc/dropbear`
entre reinícios. Imagem base não compartilha chave privada de host. Login remoto por
senha está desabilitado (`dropbear -s`); serviço não sobe sem chave pública provisionada.
Regravar raiz pode mudar chave de host: use impressão digital do aparelho conhecido
para verificar mudança, sem desabilitar verificação de host no cliente SSH.

## Acessar a partir do PC

Obtenha IP do Pi na concessão DHCP do roteador. Primeiro ensaio pode usar cabo de
rede para manter acesso administrativo independente do Wi-Fi de visitantes.

```bash
ssh -i "$HOME/.ssh/id_ed25519_labeco" root@IP_DO_PI
elo-diagnose
```

Para executar diagnóstico diretamente:

```bash
ssh -i "$HOME/.ssh/id_ed25519_labeco" root@IP_DO_PI elo-diagnose
```

Para parar e reabrir apresentação remotamente:

```sh
/etc/init.d/S50elo-client stop
/etc/init.d/S50elo-client start
```

SSH permanece acessível com cliente parado. Não é necessário sair da interface gráfica
ou usar teclado conectado ao totem.

## Relógio e HTTPS

`S42elo-clock` restaura um limite inferior de horário UTC registrado no PC durante
provisionamento. Não retrocede relógio já mais recente. Ao desligar normalmente,
preserva horário mais recente em `/var/lib/elo-time/last-good-utc`.

Chrony inicia antes do cliente e tenta sincronizar novamente quando rede/DNS ficam
disponíveis. Fontes configuradas em `/etc/chrony.conf`; administrador pode trocar por
NTP da instituição. Referência local é auxílio de bootstrap, não confirmação de relógio
sincronizado. `chronyc tracking` e `chronyc sources` distinguem esses estados.

TLS continua validando CA, nome/IP e datas do certificado. Nenhuma exceção ignora erros
TLS. Requisições do cliente repetem automaticamente após rede/horário corrigidos.

## Diagnóstico sem expor credenciais

`elo-diagnose` mostra UTC, estado do chrony, endereços/rotas, associação Wi-Fi, processos,
último frame, teste HTTPS e últimas mensagens do cliente. Não imprime arquivo de senha,
PSK, token ou chave privada. Comando adicional `elo-network-probe` funciona sem display:

```sh
elo-network-probe --server https://10.163.80.176:8443/v1/presentation \
  --token-file /etc/elo-terminal/terminal.token --ca-file /etc/elo-terminal/ca.pem
```

HTTP 200 confirma transporte HTTPS autenticado e autorizado; ferramenta não substitui
validação editorial ou prova física de imagem no monitor. Erros TLS, códigos de rede e
HTTP são explicitados. Conteúdo da resposta e cabeçalho Authorization não são impressos.

Problema do Pi anterior ainda não foi diagnosticado no hardware. Relógio sem sincronização
era uma lacuna constatada na imagem, não uma causa única comprovada da ausência de contato.
Wi-Fi, roteamento entre visitantes/cabo e firmware precisam de ensaio físico.

[Evidência da nova imagem](../evidence/C7-REMOTE-MAINTENANCE-20261110.md).

## Recuperação depois de indisponibilidade de rede

Após erro de transporte, cliente descarta conexões HTTP reutilizáveis antes da
próxima tentativa em que gerenciador estiver livre. Não interrompe requisição em
andamento nem reinicia apresentação. Tentativas continuam com intervalo limitado a
60 segundos; cache permanece disponível. CA, hostname e datas TLS continuam validados.

Wi-Fi solicita respostas DHCP por broadcast, envia hostname e tenta novamente após
três segundos quando não recebe concessão. Associação ao AP não garante endereço IP:
`wpa_state=COMPLETED` e IPv4 devem ser conferidos separadamente em `elo-diagnose`.
Restrições da rede de visitantes não podem ser removidas pelo cliente.
