# Toque para revelar

[Modo automático sem mouse](automatic-playback.md) revela conteúdo na entrada da página.
Descrição abaixo aplica-se ao modo manual.

Cliente apresenta variantes ELO `interaction: reveal` com título visível, instrução
“Toque em Revelar para descobrir.” e botão Revelar. Toque, Enter ou Espaço no botão
exibe texto editorial e imagem opcional. Navegação para próxima página continua livre.

## Usar

1. Feche cliente antigo e execute `./scripts/run-thin-client.sh` dentro de ELO-OS.
2. No painel `https://localhost:8443/`, clique Atualizar.
3. Selecione variante **Cardeal-amarelo (Gubernatrix cristata)**
   (`var_cardeal_reveal_01`), identificada como **Toque para revelar**.
4. Publique seleção. Cliente consulta atualização em até 30 segundos; clique
   Recomeçar para aplicar. Na página, clique Revelar.

Voltar preserva revelações durante sessão. Recomeçar limpa todas, inclusive quando
já está na primeira página. Reinício começa oculto. Funciona sem servidor depois
do download. Seleção operacional e conteúdo editorial não são alterados pelo teste.

Prévia isolada pode ser criada e executada com:

```bash
python3 scripts/elo_import.py "$HOME/.local/share/elo/content/current" \
  --content-dir "$PWD/build/elo-reveal-content" --variant var_cardeal_reveal_01
./scripts/run-client.sh --content-dir "$PWD/build/elo-reveal-content"
```

## Contrato

Formato local 3, schema 1: página inclui `interaction: "reveal"` além de título,
corpo e imagem opcional. Páginas sem interação continuam permitidas na mesma seleção.
Limites e validações de imagem permanecem [os mesmos](image-content.md).

Cliente anuncia `text-v1,image-v2,reveal-v3`. Servidor exige `reveal-v3` para formato 3
mais `image-v2` quando houver imagem. Cliente anterior recebe HTTP 409 e preserva cache.

Conteúdo revelado permanece no catálogo local; ocultação é apresentação, não sigilo.
Estado de revelação fica só em memória. Nenhuma resposta ou evento de toque é enviado.
Recibo confirma publicação apresentada, inclusive sua tela inicial oculta; não comprova
que visitante clicou Revelar. Hash da publicação permanece igual ao revelar.

Implementação cobre ação local de mostrar texto/imagem. Não executa receitas ELO,
perguntas, escolhas, pontuação, áudio, vídeo ou navegação por relações.

## Validação

Ensaios nativos cobrem ocultação, toque/teclado, imagem decodificada, navegação,
Recomeçar, mudança de rede, capacidade HTTPS e reinício offline. Importador rejeita
interação em formatos antigos e interações incompatíveis. Buildroot/Pi 5 não foi
recompilado nem validado nesta entrega.
