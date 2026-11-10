# Reprodução supervisionada sem entrada humana

Na bancada Fedora, feche cliente aberto e execute dentro de ELO-OS:

```bash
./scripts/run-supervised-thin-client.sh
```

Lançador compila uma vez e abre tela cheia com mesmo servidor, credenciais e cache
de `run-thin-client.sh`. Supervisor acompanha frames apresentados. Encerramento do
processo ou ausência de progresso dos frames causa reinício automático, com espera
progressiva. Cache mantém conteúdo e tempo definidos pelo servidor. Sessão reiniciada
começa na primeira página; não restaura posição anterior.

Variáveis `ELO_SERVER_URL`, `ELO_CONTENT_DIR`, `ELO_CLIENT_TOKEN_FILE` e
`ELO_SERVER_CA_FILE` permitem configurar outra instalação. Runtime privado fica em
`$XDG_RUNTIME_DIR/elo-client`, separado do conteúdo persistente. `ELO_RUNTIME_DIR`
pode fornecer diretório alternativo. Reutiliza supervisor existente dos perfis GUI.
Não execute junto de outro cliente operacional usando mesma identidade de terminal.

Supervisor aguarda até 30 s pelo primeiro frame, detecta falta de progresso em 7 s
e permite até cinco reinícios por janela de cinco minutos. Falha persistente termina
supervisor com erro, permitindo que serviço de inicialização aplique política externa.
Tela de erro responsiva não equivale a conteúdo operacional pronto.

[Instalador de terminais](terminal-provisioning.md) agora prepara autostart no PC
e boot configurado no Pi. Lançador de bancada isoladamente não instala autostart. Integração definitiva
ao boot depende do destino: sessão gráfica Linux ou perfil embarcado Raspberry Pi.
Perfil Pi 5 mantém lançamento manual quando não provisionado. Validação física
continua pendente; ensaio do supervisor não comprova recuperação em hardware físico.

## Verificação

```bash
python3 tests/client/automatic-recovery-test.py
```

Teste usa cliente Qt real offscreen, cache isolado em formato 4, exposição de 5 s,
sem servidor. Aplica SIGKILL e SIGSTOP; verifica novo processo, novos frames,
avanço até segunda página e integridade do cache após cada recuperação. Arquivos
operacionais e serviços do usuário não são alterados. Não substitui teste de boot,
painel físico, energia ou tela preta com frames ainda avançando.
