# Pi 5: cliente local e Wi-Fi experimentais

Perfil `pi5-client`, separado de `pi5` e dos perfis QEMU. A base de console iniciou
fisicamente com login conforme relato do operador em 2026-11-09; a combinação
cliente/Wi-Fi deste perfil ainda requer ensaio físico. Não é integração com ELO Server.

## Construção

```sh
PROFILE=pi5-client JOBS=32 ./scripts/build.sh
PROFILE=pi5-client ./scripts/inspect-image.sh
```

No desktop preparado, prefixe o build com `toolbox run -c elo-os env`.
Saída: `output/pi5-client/images/sdcard.img`, raiz ext4 de 512 MiB.
Guarde imagem anterior e faça backup do cartão antes de substituir a mídia.
O destino deste perfil é microSD diretamente no slot do Pi, com
`root=/dev/mmcblk0p2`. Um leitor USB no Fedora não muda esse destino.

A cmdline mantém `module_blacklist=vc4`: no ensaio anterior o console chegou a
login com VC4 bloqueado. Com carregamento explícito do módulo, a última tela
mostrou mensagens VC4 e o operador relatou falta de resposta ao teclado.
Isso indica uma área a investigar, não comprova a causa de um travamento.
O overlay do Pi 5 e o framebuffer de firmware são preservados. Nenhuma
alegação de KMS/V3D/EGLFS validado decorre deste perfil.

## Console e cliente

Primeiro confira login, teclado e framebuffer:

```sh
cat /etc/elo-os-release
cat /proc/cmdline
cat /proc/fb
ls -l /dev/fb0 /dev/input/event*
elo-client-start
```

O lançador usa Qt LinuxFB em `/dev/fb0`, Qt Quick por CPU e fontes DejaVu;
não usa DRM, EGLFS, supervisor nem inicia automaticamente no boot.
Teste as páginas e navegação offline antes da rede. Pressione Escape para encerrar
a sessão de bancada e retornar ao console. O parâmetro `--exit-on-escape` é
explícito; outros perfis não mudam de comportamento. Não corte energia durante escrita.

Ausência de `/dev/fb0`, falha do plugin LinuxFB, tela incorreta ou falta de
teclado devem ser registradas; não remova o bloqueio de VC4 para contornar.

## Wi-Fi WPA2-Personal

Não há credenciais incorporadas. No console do Pi, como root:

```sh
iw dev
dmesg | grep -i -e brcm -e firmware
elo-wifi-connect BR 'Nome da rede'
wpa_cli -i wlan0 status
ip -4 addr show wlan0
ip route
```

Substitua `BR` pelo país onde o dispositivo opera. A senha é lida sem eco no
terminal, nunca como argumento. O arquivo `/etc/elo-wifi.conf` guarda SSID e
chave derivada, com modo 0600; a chave também é segredo. O perfil mantém raiz
RW e não oferece ainda cofre de credenciais ou appliance imutável.

A rede configurada é retomada por `S41elo-wifi` nas próximas partidas.
Sem configuração, não há tentativa de conexão. Ethernet permanece disponível.
O cliente deve funcionar também sem AP ou Ethernet. O comando de configuração
não comprova associação: exija `wpa_state=COMPLETED`, endereço e rota. Teste
alcance ao gateway e DNS separadamente. WPA3 exclusivo, redes corporativas e
portais cativos ficam fora deste primeiro roteiro.

Registre boots, associação, DHCP, perda/reconexão e navegação do cliente. Use
`poweroff` e confirme encerramento antes de remover o cartão.

## Ensaios automatizados de bancada

```sh
python3 tests/network/pi5-tools-test.py
toolbox run -c elo-os python3 tests/client/pi5-rootfs-smoke.py
```

O primeiro usa `wpa_passphrase` nativo e terminal PTY, com `/etc` redirecionado
para diretório temporário e serviço de rede simulado; verifica derivação real da
chave, ausência de senha no eco/arquivo, SSIDs especiais, permissões e rejeição de
entradas inválidas. Não associa uma interface Wi-Fi.

O segundo requer imagem pronta em `output/pi5-client` e kernel ARM64 virtual em
`output/toolbox/qemu-aarch64-gui/images/Image` (ou `QEMU_TEST_KERNEL`). Usa snapshot,
sem NIC, renderização LinuxFB real, teclado virtual e Escape. Guarda relatório e
frames em `output/pi5-client`. A CPU virtual `max` suporta instruções ARMv8.2 usadas no Cortex-A76;
Cortex-A53 não é suficiente. O kernel é genérico: o teste não inicializa firmware,
GPU, rádio nem kernel físico do Pi 5. Não executar durante build da imagem.

Build e raiz virtual passaram em 2026-11-09; consulte [evidência da imagem](../evidence/P2-PI5-CLIENT-BUILT-20261109.md). Validação física do cliente e Wi-Fi permanece pendente.
