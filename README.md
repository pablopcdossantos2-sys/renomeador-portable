# Renomeador Portátil

Aplicativo gratuito para Windows que renomeia vários arquivos de uma pasta usando regras simples, com pré-visualização e opção para desfazer o último lote.

## O que faz

- Remove uma quantidade de caracteres do início ou do final do nome, preservando a extensão.
- Remove vários termos, separados por vírgula.
- Substitui um texto por outro, com opção de ignorar maiúsculas/minúsculas.
- Adiciona prefixo e sufixo.
- Converte nomes para MAIÚSCULAS, minúsculas ou aplica capitalização inteligente de títulos em português ou inglês.
- Deixa conectivos como “de”, “da”, “e”, “of”, “the” em minúsculas no meio do título, mantendo a primeira palavra capitalizada.
- Opcionalmente corrige a ortografia em português ou inglês usando dicionários locais, sem enviar nomes de arquivos para a internet.
- Mostra os nomes propostos antes de alterar qualquer arquivo.
- Detecta nomes inválidos, destinos ocupados e colisões entre arquivos.
- Permite desfazer o último lote bem-sucedido, desde que os arquivos ainda estejam nos nomes esperados.

O aplicativo trabalha somente com arquivos diretamente dentro da pasta escolhida. Ele não altera arquivos dentro de subpastas e mantém as extensões.

## Como usar no Windows

### Opção 1 — Executável portátil

1. Abra a aba **Actions** deste repositório.
2. Entre na execução mais recente bem-sucedida do fluxo **Testes e executável Windows**.
3. Na seção **Artifacts**, baixe **RenomeadorPortable-Windows**.
4. Extraia o ZIP e abra **RenomeadorPortable.exe**.

O executável inclui os dicionários necessários à correção ortográfica e não exige Python instalado ou uma instalação tradicional. O Windows pode exibir um aviso de segurança para programas baixados da internet; confira se o arquivo foi baixado deste repositório antes de optar por executá-lo.

Para publicar uma versão sem instalar Git no computador: abra **Actions → Testes e executável Windows → Run workflow**, selecione a branch main e informe uma versão como v0.1.0 no campo de versão. Deixe o campo vazio para apenas gerar o executável. Após a execução bem-sucedida, a versão será publicada em **Releases** com o EXE e o ZIP.

### Opção 2 — Executar o código-fonte

É necessário ter Python 3.10 ou mais recente instalado com o componente **Tkinter**.

1. Baixe o repositório pelo botão **Code → Download ZIP** e extraia os arquivos.
2. (Opcional, mas recomendado) Abra um terminal nessa pasta e instale a dependência de correção ortográfica:

    py -m pip install -r requirements.txt

3. Abra main.py com Python ou execute no terminal:

    py main.py

Sem o pacote `pyspellchecker`, o programa ainda pode fazer renomeações e aplicar regras de capitalização; apenas a opção de correção ortográfica ficará indisponível.

## Passo a passo

1. Selecione a pasta que contém os arquivos.
2. Configure uma ou mais regras. As regras são aplicadas nesta ordem: cortar caracteres, remover termos, substituir texto, normalizar espaços, acrescentar prefixo/sufixo, corrigir ortografia (se ativada) e aplicar a capitalização escolhida.
3. Escolha **Título inteligente (PT-BR)** ou **Title Case (English)** para capitalizar títulos com os conectivos habituais em minúsculas. A extensão do arquivo não é alterada.
4. Opcionalmente, marque **Corrigir ortografia automaticamente** e selecione **Português (Brasil)** ou **English**.
5. Clique em **Pré-visualizar**. Linhas marcadas como **Conflito** precisam ser corrigidas antes de prosseguir.
6. Clique em **Renomear arquivos** e confirme a operação.
7. Para reverter o último lote, selecione a mesma pasta e clique em **Desfazer último lote**.

O atalho **Ctrl + Enter** abre a pré-visualização.

**Exemplo:** para converter `2024_relatorio final.pdf` em `Relatorio Final.pdf`, use **Do início = 5** e **Título inteligente (PT-BR)**. Se também ativar a correção ortográfica em português, o corretor poderá sugerir `Relatório Final.pdf`.

## Capitalização inteligente

O modo **Título inteligente (PT-BR)** mantém em minúsculas conectivos como *a, as, o, os, um, uma, de, da, das, do, dos, e, em, por, para, com, sem, no, na, nos, nas, ao, à, às, pelo* e *pela*, exceto quando a palavra estiver no início do nome.

O modo **Title Case (English)** aplica uma regra equivalente a conectivos ingleses como *a, an, the, and, but, or, as, at, by, for, in, of, on, to, from, with* e *without*, exceto no início do nome. As listas são práticas e não substituem um manual editorial para nomes próprios ou títulos de estilos específicos. Siglas comuns como PDF, API, HTML e NASA são preservadas.

## Correção ortográfica: limitações

A correção é **opcional, local e baseada em frequência de palavras**, não uma revisão gramatical completa. Ela pode sugerir uma palavra comum no lugar de um nome próprio, nome de pessoa, marca, modelo, sigla não reconhecida, termo técnico ou palavra estrangeira. Por isso:

- Deixe a opção desativada quando os nomes contiverem muitos nomes próprios, marcas, códigos ou vocabulário específico.
- Confira a coluna **Novo nome** na pré-visualização antes de executar qualquer lote.
- O recurso tenta preservar a capitalização original e ignora siglas em maiúsculas e palavras com capitalização interna, mas essas heurísticas não eliminam todos os erros possíveis.

O corretor utiliza dicionários locais de português e inglês; não consulta um serviço online nem envia nomes de arquivos para terceiros. Seu dicionário é útil para erros ortográficos comuns, mas não decide sozinho se uma palavra está correta no contexto.

## Histórico e proteção contra conflitos

O histórico do último lote é guardado na pasta selecionada, no arquivo `.renomeador_portable_historico.json`. O programa exclui esse arquivo da lista de renomeação. Um novo lote bem-sucedido substitui o histórico anterior; portanto, só o lote mais recente pode ser desfeito.

Antes de renomear, o programa verifica destinos duplicados, nomes reservados do Windows e arquivos ou pastas que já ocupem o destino. A operação é feita em duas fases com nomes temporários para permitir trocas como `a.txt` para `b.txt` e `b.txt` para `a.txt`. Se uma etapa falhar, o programa tenta restaurar os nomes anteriores.

Evite mover, excluir ou renomear manualmente os arquivos entre a renomeação e a opção de desfazer. Como acontece com qualquer alteração de arquivos, mantenha cópias de segurança de dados importantes.

## Desenvolvimento e testes

A interface é feita com Tkinter; a lógica de arquivos fica em `renamer.py`. O pacote `pyspellchecker` é usado para correção ortográfica opcional e é incluído no executável portátil.

Para rodar os testes, execute no PowerShell, a partir da pasta do projeto:

    py -m unittest discover -s tests -v

O GitHub Actions executa os testes e empacota o programa como um executável Windows de arquivo único. É possível publicar um Release com o EXE e o ZIP tanto ao enviar uma tag `vMAJOR.MINOR.PATCH` quanto pela opção manual descrita acima.

## Licença

Ainda não foi definida uma licença de redistribuição para este repositório.
