# Painel local de conteúdo e distribuição

Página inicial: **https://localhost:8443/**. Estúdio: **https://localhost:8443/studio/**.
A primeira página substitui o JSON `unauthorized` exibido ao abrir a raiz da API.
A API do terminal `/v1/presentation` continua exigindo a credencial própria.

## Acessar

No terminal do Fedora, consulte a chave administrativa local e copie para o campo
de login da página inicial:

```bash
cat "$HOME/.config/elo-distribution/admin.token"
```

Não use `terminal.token`: essa chave não permite operações administrativas.
A chave não aparece em logs, URLs nem no HTML. O navegador guarda a credencial
administrativa no sessionStorage da aba; Sair remove essa credencial. O Estúdio
reutiliza a sessão da mesma aba, sem solicitar outra chave.

Certificado HTTPS é local, confiado explicitamente pelo cliente Qt; confiança do
navegador não foi alterada. Isso explica o aviso de certificado mostrado no navegador.

## Fluxo

1. Abra **Estúdio editorial** para editar átomos/aplicações, subir mídia e publicar
   uma versão ELO. É o frontend e backend existentes no projeto ELO, não outro banco
   editorial. O workspace existente continua em `$HOME/.local/share/elo/content`.
2. Volte a **Distribuição** e Atualizar. O painel lê o bundle ELO publicado em `current`.
3. Selecione variantes na ordem desejada e confira a prévia. Variantes de texto e uma imagem PNG/JPEG podem ser selecionadas com cliente atualizado.
   Áudio e interações continuam recursos do editor ainda não executados pelo cliente.
4. Clique **Publicar seleção para o cliente**. Isso persiste a seleção de distribuição;
   não cria nem altera versão editorial. O hash da publicação é revalidado para evitar
   confirmar uma seleção sobre publicação que mudou enquanto a página estava aberta.
5. Cliente consulta a cada 30 segundos, guarda conteúdo validado e avisa atualização.
   Recomeçar aplica a nova apresentação. O painel distingue recebimento e apresentação e mostra horário da última comunicação.

Salvar no editor não equivale a publicar uma versão. Subir uma imagem também não
faz o cliente textual passar a renderizar imagens. Uma seleção incompatível com uma
publicação futura produz recusa de distribuição; cache do cliente permanece válido.

## Serviços e persistência

- `elo-content.service`: HTTPS em 127.0.0.1:8443; landing page, seleção e gateway editorial.
- `elo-studio.service`: backend C++ ELO existente em 127.0.0.1:18080, acessado pelo gateway.
- Seleção: `$HOME/.local/share/elo-distribution/state/selection.json`, escrita atômica
  com fsync. Reinício do daemon preserva seleção. O argumento `--variant` é o padrão
  somente enquanto não existir seleção persistida.
- Admin: `$HOME/.config/elo-distribution/admin.token`, distinto da credencial do terminal.

Ambos os serviços estão habilitados. Instalador `scripts/install-content-service.py`
agora instala os dois; aceita `--elo-root` para localizar checkout ELO e seu
`build/apps/elo-admin/elo-admin` previamente compilado. Backend editorial depende desse
binário e da montagem do checkout. Não foi recompilado ELO nesta etapa; foi usado
binário existente. Código-fonte do repositório ELO permanece inalterado.

```bash
systemctl --user status elo-content.service elo-studio.service
journalctl --user -u elo-content.service -u elo-studio.service -f
```

Distribuição só escreve seu diretório de estado. Backend editorial tem escrita no
workspace do ELO, como requerido para edição/upload/publicação. Chave de terminal
não é encaminhada ao backend editorial. Gateway encaminha somente rotas editoriais
e mídia para endereço loopback fixo; rejeita Origin externo em operações administrativas.
Prévia de mídia usa cookie HttpOnly/SameSite=Strict restrito a `/studio/assets/`, sem
permitir acesso administrativo por cookie. Cookie é removido ao Sair no painel.

A cópia implantada do frontend recebe paleta MORFO, fontes locais e link de retorno.
Controles do antigo processo kiosk foram ocultados: não representam controle deste
thin client. Foi corrigida somente na cópia implantada uma chave CSS ausente em
`.form-hint` do frontend original, que fazia estilos seguintes virarem regras aninhadas.
O arquivo do projeto ELO não foi alterado.

## Verificação

```bash
python3 tests/network/panel-test.py
python3 tests/network/distribution-test.py
./tests/smoke.sh
```

Testes do painel cobrem permissões separadas, landing pública sem dados editoriais,
seleção persistente e ordenada, recusa por hash desatualizado/capacidade/Origin,
encaminhamento editorial e sessão restrita de mídia. Ensaio em navegador e upload
nativo isolado registrados na [evidência](../evidence/D2-SERVER-PANEL-20261110.md).

Continuidade: [confirmações de entrega e correção de ativação](delivery-receipts.md).

Produções externas: [integração Sister-Studio e pré-validação de consumíveis](sister-consumables.md).
O catálogo editorial continuará no ELO. A recepção autenticada está habilitada
nesta instalação, com produções em quarentena na aba **Produções Sister-Studio**.

## Publicação de alterações com imagem

Uma versão publicada é imutável. Ao adicionar imagem ou alterar conteúdo de uma
versão já publicada, o Studio abre **Publicar nova versão**, sugere o próximo patch
disponível e permite editar o número. Confirmar salva o plano com essa versão e
publica novamente; Cancelar mantém a versão anterior. Erros de validação não
disparam incremento automático. O mesmo fluxo atende ao botão superior, à lista
de aplicações e ao editor. O botão superior usa a aplicação exibida no cabeçalho,
sem usar inadvertidamente o plano carregado no formulário oculto.

Variantes sem imagem/vídeo próprio herdam a única imagem em `modalities.image`
do átomo. Uma imagem explícita da variante prevalece; múltiplas imagens padrão
exigem seleção explícita. Publicar versão editorial continua separado de selecionar
e distribuir variantes no painel. Clientes precisam declarar `image-v2`.

O instalador adapta as três ações de publicação na cópia do frontend ELO e inclui
`web/distribution/studio-publishing.js`. Se o frontend de origem mudar essas ações,
o instalador recusa a adaptação para revisão, em vez de aplicar uma substituição parcial.
Após atualizar a cópia instalada, recarregue a página com `Ctrl+Shift+R`.

[Capacidade de texto e imagem](image-content.md).
