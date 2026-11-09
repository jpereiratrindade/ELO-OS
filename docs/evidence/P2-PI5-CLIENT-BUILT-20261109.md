# Pi 5 cliente/Wi-Fi — imagem compilada e raiz validada virtualmente

Data: 2026-11-09, America/Sao_Paulo. Perfil: `pi5-client`.
Fonte dos componentes da imagem: commit `57b0323`.
Buildroot 2026.08.1, Toolbox Fedora 44, 32 jobs; build terminou com sucesso.

Imagem local: `output/pi5-client/images/sdcard.img`, 570425856 bytes.
SHA-256: `9b9fa73de74bf983bcc7702924a9c5a9996c04ed2a2eaa46ddf53b2fadc0ebfd`.
Raiz ext4: 512 MiB, SHA-256
`4e9848d56aeebbcbd14b24aa303aeefafc78567e50bceb1f660f315a54d10b8d`.

| Verificação | Resultado e escopo |
| --- | --- |
| Build completo Pi 5 | PASS; kernel, DTBs, firmware, Qt e cliente instalados |
| Preflight de imagem | PASS; hash, limites MBR e assinaturas FAT16/ext4 |
| Integridade FAT/ext4 | PASS; fsck.fat -n e e2fsck -fn, sem escrita |
| Conteúdo de partições na imagem | PASS; comparação byte a byte com boot.vfat/rootfs.ext4 |
| Firmware Wi-Fi Pi 5 | binário, NVRAM e CLM presentes e links resolvidos; não comprova associação |
| Testes existentes e Kconfig | PASS; smoke do repositório e oito perfis |
| Configurador Wi-Fi | PASS; testes PTY com derivação real de chave, senha sem eco, permissão 0600 e entradas inválidas |
| Cliente nativo | PASS; contratos do núcleo e interface |
| Raiz nova em QEMU ARM64 | PASS; framebuffer, apresentação offline, navegação, saída por Escape e shutdown |
| Cliente e Wi-Fi no Pi físico | NOT TESTED nesta nova imagem |

Ensaio virtual: kernel ARM64 `virt` existente, QEMU TCG com CPU `max`, snapshot e
sem NIC. Os binários do Pi usam instruções ARMv8.2 do Cortex-A76; Cortex-A53 não
é CPU válida para esse ensaio. Captura de tela espera a atualização assíncrona
do framebuffer antes de comparar pixels. Hash da raiz permaneceu idêntico após
desligamento. Foram inspecionados frames de apresentação; página 1 e página 2
produziram pixels diferentes.

Isso valida aplicação/raiz com kernel virtual; não inicializa firmware, GPU,
rádio nem kernel físico do Pi. Não declara correção de VC4. A imagem preserva
`module_blacklist=vc4`, raiz microSD e cliente manual via `elo-client-start`.

Artefatos locais, não versionados: `output/pi5-client/{build.log,preflight.json,
build-inventory.json,software-inventory.json,rootfs-qemu.json,rootfs-qemu.log}`,
frames `rootfs-{ready,next}.ppm` e manifesto `images/sdcard.img.sha256`.
Roteiro: [Pi 5 cliente e Wi-Fi](../tests/pi5-client-wifi.md).
