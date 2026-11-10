# Conteúdo editorial ELO no cliente local

Implementado em 2026-11-10: projeção explícita de variantes textuais de um bundle
ELO selado para o catálogo local do ELO/OS. O importador usa os campos e o algoritmo
`ContentBundle::compute_content_hash()` do checkout ELO, incluindo os caminhos
relativos antes dos bytes de cada arquivo em `catalog/` e `assets/`.
Compatibilidade consultada: `include/elo/content/content_bundle.hpp`,
`src/content/content_bundle.cpp`, `src/content/content_catalog.cpp` e
`docs/CONTENT_MODEL_V0.2.md` do ELO.

## Executar no host

Escolha um bundle já publicado pelo ELO; `current` pode apontar para ele. Não use
o workspace editorial mutável como substituto de uma publicação.

```bash
python3 scripts/elo_import.py "$HOME/.local/share/elo/content/current" \
  --content-dir "$PWD/build/elo-real-content" \
  --variant var_cardeal_ambient_01
./scripts/run-client.sh --content-dir "$PWD/build/elo-real-content"
```

O identificador acima pertence ao bundle de bancada encontrado nesta máquina.
Para outra aplicação, selecione seus próprios `variant_id` em `catalog/variants/`.
Repita `--variant` na ordem de apresentação desejada, até 32 variantes. A escolha
é do operador, sem seleção probabilística, execução de receitas ou personalização.
A saída JSON registra bundle, versão, hash original, hash da apresentação e seleção;
ela pode ser guardada pelo operador como recibo da importação.

O importador é ferramenta Python do host. Não acrescenta Python à imagem Buildroot.
Para a primeira instalação no terminal, transfira o diretório resultante com o
cliente parado para armazenamento persistente previamente preparado e inicie `elo-client` com
`--content-dir /caminho/absoluto`. No perfil Pi 5, `elo-client-start` aceita esse
argumento. Não há transferência automática nem seleção automática de `/data`.
O diretório precisa ser legível pelo usuário do cliente. Com o cliente já aberto,
novas ativações pelo protocolo local são detectadas a cada dois segundos. A tela
anuncia conteúdo disponível e mantém a navegação atual. Clique **Recomeçar** (ou
pressione Home) para validar novamente o apontador e iniciar a nova apresentação.
Não é necessário reiniciar o processo. Reimportação idêntica não muda a sessão.

Uma falha de leitura, integridade ou estrutura mostra aviso separado sem substituir
a apresentação em memória. Uma versão pendente deixa de ser elegível se o apontador
for alterado ou corrompido antes de Recomeçar. A ativação confirmada espera novo frame
para voltar ao estado pronto. Esta preservação em memória dura enquanto o processo
estiver vivo; reinício continua exigindo catálogo válido em disco.

## Contrato de capacidade

- Manifesto ELO `schema_version` 0.1 ou 0.2, com hash SHA-256 obrigatório.
- No schema 0.2, seleção explícita por `atom_ids`; no 0.1, lista vazia significa todos.
- Variante deve referenciar átomo presente e autorizado pela seleção do manifesto.
- Somente `interaction: none`, título e texto; sem mídia, opções ou resposta correta.
- Não usa resumo do átomo para substituir uma variante incompatível.
- Metadados adicionais do domínio não são executados. Variantes não selecionadas,
  relações e receitas não fazem parte da experiência projetada.
- Hash verifica todos os arquivos de catálogo/assets antes da projeção. Arquivos
  internos simbólicos/especiais são recusados. Limites: 1.024 arquivos, 8 MiB por
  arquivo e 32 MiB no total; permanecem os limites menores do catálogo do cliente.
- Duplicação de chaves JSON ou identidades é recusada. Falhas anteriores à publicação
  preservam o apontador ativo. Publicação com fsync inconclusivo retorna código 3,
  como o ativador local existente, exigindo reconciliação do estado.

O catálogo de destino usa formato local 1; a versão editorial original aparece no
nome apresentado. Hash original e IDs de variantes ficam no recibo, não são eventos
nem prova de procedência autenticada. Importação não modifica o bundle ELO.

## Limites do marco

Entrada pressupõe operador e diretório de origem confiáveis, sem alterações
concorrentes. SHA-256 não autentica editor ou servidor; o manifesto ELO não está
incluído nesse hash nativo. Esta ponte não oferece sincronização, identidade de
terminal, TLS, fila durável, execução completa do ELO ou isolamento de privilégios.
I2–I4 e integração funcional I6 continuam com critérios próprios no IMPL-003.

Verificação reproduzível:

```bash
python3 tests/client/elo-import-test.py
./tests/smoke.sh
```

Os testes cobrem importação e reabertura, idempotência, seleção ordenada, schemas,
alteração de assets/catálogo, duplicação, links e capacidades incompatíveis com
preservação do apontador anterior. A ativação e falhas de persistência continuam
cobertas por `tests/client/local-content-test.py`.

Ensaio com bundle publicado real: [evidência de 2026-11-10](../evidence/I3-ELO-TEXT-20261110.md).

Continuidade implementada: [distribuição HTTPS e daemon local](distribution.md). O importador permanece ferramenta offline independente.
