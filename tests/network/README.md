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
