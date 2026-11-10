# Preparar PC e Raspberry Pi 5 sem mouse ou teclado

Configuração feita uma vez, no PC de preparação. Totem recebe servidor, credencial,
Wi-Fi e conteúdo inicial antes de ligar. No boot, inicia rede e cliente em tela cheia;
cache permite apresentar sem servidor. Não exige login no console do Pi.

## PC de testes

Compile cliente com `./scripts/run-client.sh` e feche janela. Depois:

```bash
python3 scripts/install-terminal.py --platform pc \
  --server https://localhost:8443/v1/presentation \
  --token-file "$HOME/.config/elo-distribution/terminal.token" \
  --ca-file "$HOME/.config/elo-distribution/server.crt" --activate --start
```

Instala cópia do binário e supervisor em `~/.local/share/elo-terminal/bin`.
Configuração em `~/.config/elo-terminal`, cache já existente preservado.
Serviço `elo-client.service` inicia com sessão gráfica do usuário. Isso não configura
login automático no computador. Nesta bancada serviço já está instalado e habilitado. Ensaios confirmaram frames em offscreen
e na sessão gráfica; serviço pode ser iniciado/parado pelos comandos abaixo.

```bash
systemctl --user start elo-client.service
systemctl --user stop elo-client.service
systemctl --user disable --now elo-client.service
```

Reexecute instalador depois de compilar nova versão para atualizar binário instalado.
Não execute simultaneamente cliente manual usando mesma identidade operacional.

## Raspberry Pi 5

Compile imagem atualizada com `PROFILE=pi5-client JOBS=32 ./scripts/build.sh`.
Provisionamento opera numa raiz ext4 já montada, como `/mnt/elo-root`; não grava
imagem em cartão, formata dispositivo ou monta partição automaticamente. O alvo deve
conter cliente ARM64, `/etc/os-release` e `/etc/init.d` do perfil `pi5-client`.

Com raiz do cartão montada para escrita, execute no PC de preparação:

```bash
sudo python3 scripts/install-terminal.py --platform pi5 --root /mnt/elo-root \
  --server https://SERVIDOR-NA-REDE:8443/v1/presentation \
  --token-file /caminho/terminal.token --ca-file /caminho/ca.pem \
  --seed-content /caminho/cache-validado-do-pc \
  --wifi-ssid 'NOME DA REDE' --wifi-country BR \
  --ssh-authorized-key /caminho/chave-publica.pub
```

Use caminhos absolutos quando executar via sudo. Senha Wi-Fi é solicitada localmente,
sem eco, sem argumento de processo e sem impressão em logs. São aceitas redes
WPA2-Personal com senha ASCII imprimível de 8 a 63 caracteres e SSID de 1 a 32 bytes.
Configuração guarda chave PSK derivada por PBKDF2, sem senha em texto, em arquivo 0600.
PSK continua sendo credencial de acesso à rede e deve permanecer privada.

Automação de bancada pode fornecer `--wifi-password-file /caminho/arquivo-privado`,
arquivo regular 0600, em vez do prompt. Não há opção para senha direta na linha de
comando. Sem opções Wi-Fi, configuração de rede anterior é preservada, permitindo
uso só de Ethernet.

Conteúdo inicial deve ser cache válido do modo automático (formato 4). Se destino já
possui cache válido, pode omitir `--seed-content`; instalador preserva cache existente.
Isso garante primeira apresentação offline. Use cache do PC depois que recebeu
programação de exposição do servidor. Não copie credencial administrativa ou chave
privada do servidor para Pi.

A sequência no boot:

1. Rede Wi-Fi configurada sobe com wpa_supplicant e DHCP em segundo plano.
2. `S50elo-client` inicia supervisor sem exigir conexão estabelecida.
3. Cliente apresenta cache local e consulta servidor quando rede estiver disponível.
4. Sequência avança pelo tempo programado; atualização entra ao fim de ciclo.
5. Supervisor recupera encerramentos e travamentos de frames dentro de política de
   reinícios limitada. Falha persistente pode exigir intervenção administrativa.

`consoleblank=0` no perfil atualizado evita apagamento do console por inatividade.
Sem configuração do servidor, serviço automático não inicia; bancada manual continua
acessível com `elo-client-start`. Com configuração, esse comando também usa terminal
provisionado. Não é necessário teclado para operação normal depois de provisionado.

## Servidor acessível pela rede

Nesta bancada servidor está acessível em **https://10.163.80.176:8443/** pelo cabo,
com certificado local contendo esse IP e localhost. Serviço escuta IPv4 na porta 8443.
Pi usará rede **CPPSUL-VISITANTES**. Comunicação entre Wi-Fi de visitantes e rede
cabeada ainda precisa ser verificada no aparelho; configuração do AP pode afetá-la.

Para reaplicar instalação LAN preservando certificado atual:

```bash
python3 scripts/install-content-service.py \
  --bundle "$HOME/.local/share/elo/content/current" --variant var_cardeal_ambient_01 \
  --host 0.0.0.0 --tls-name 10.163.80.176
```

`--renew-certificate` reemite certificado local com nomes/IPs solicitados. Depois de
reemissão, reprovisione confiança dos clientes com certificado atualizado. Nome/IP de
`--server` deve estar no certificado; verificação TLS permanece ativa.

PC e Pi agora possuem [credenciais e acompanhamento separados](terminal-monitoring.md),
permitindo ensaio simultâneo. Seleção editorial continua compartilhada.

Foi preparado roteiro local com IP, SSID e caminhos desta bancada:

```bash
./build/pi5-provisioning/configurar-pi.sh /ponto/de/montagem/da/raiz-do-pi
```

Esse comando solicita senha Wi-Fi no terminal e provisiona raiz já montada. Não grava
cartão nem escolhe disco. Script está fora do Git e não contém senha nem token em texto.

## Evidência e próximos testes

Provisionamento foi testado em diretórios temporários, incluindo hash de cache,
credenciais, Wi-Fi derivado, caminhos com espaços e metacaracteres e boot sem
configuração. Serviço PC instalado produziu frames reais Qt em offscreen e recebeu
modo automático de 15 s. Oito perfis passaram pela verificação de Kconfig.
Imagem `pi5-client` foi recompilada e passou no ensaio ARM64 sem NIC, mouse ou
teclado, incluindo JPEG, ciclo e recuperação de processo.
[Evidência](../evidence/C6-PI5-AUTOSTART-20261110.md).

No hardware ainda é necessário verificar: primeiro boot com Wi-Fi, reinício sem rede,
restabelecimento de rede, cliente após corte de energia, imagem do monitor e reconexão
AP. Não foi gravado cartão nem validado Pi físico nesta etapa.

[SSH, relógio automático e diagnóstico remoto](remote-maintenance.md) fazem parte
da nova imagem e são provisionados antes do boot do totem.
