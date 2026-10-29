# Renomeador Portátil

Aplicativo gratuito para Windows que renomeia vários arquivos de uma pasta usando regras simples, com pré-visualização e opção para desfazer o último lote.

## O que faz

- Remove uma quantidade de caracteres do início ou do final do nome, preservando a extensão.
- Remove vários termos, separados por vírgula.
- Substitui um texto por outro, com opção de ignorar maiúsculas/minúsculas.
- Adiciona prefixo e sufixo.
- Converte o nome para MAIÚSCULAS, minúsculas ou capitaliza palavras.
- Mostra os nomes propostos antes de alterar qualquer arquivo.
- Detecta nomes inválidos, destinos ocupados e colisões entre arquivos.
- Permite desfazer o último lote bem-sucedido, desde que os arquivos ainda estejam nos nomes esperados.

O aplicativo trabalha somente com arquivos diretamente dentro da pasta escolhida. Ele não altera arquivos dentro de subpastas e mantém as extensões.

## Como usar no Windows

### Opção 1 — Executável portátil

1. Abra a aba **Actions** deste repositório.
2. Entre na execução mais recente do fluxo **Testes e executável Windows**.
3. Na seção **Artifacts**, baixe **RenomeadorPortable-Windows**.
4. Extraia o ZIP e abra **RenomeadorPortable.exe**.

O executável não exige uma instalação tradicional nem Python instalado. O Windows pode exibir um aviso de segurança para programas baixados da internet; confira se o arquivo foi baixado deste repositório antes de optar por executá-lo.

Para publicar uma versão sem instalar Git no computador: abra **Actions → Testes e executável Windows → Run workflow**, selecione a branch main e informe uma versão como v0.1.0 no campo de versão. Deixe o campo vazio para apenas gerar o executável. Após a execução bem-sucedida, a versão será publicada em **Releases** com o EXE e o ZIP.

### Opção 2 — Executar o código-fonte

É necessário ter Python 3.10 ou mais recente instalado com o componente **Tkinter**. Não há dependências externas.

1. Baixe o repositório pelo botão **Code → Download ZIP** e extraia os arquivos.
2. Na pasta extraída, abra o arquivo main.py com Python. Também é possível abrir um terminal nessa pasta e executar a instrução:

    py main.py

## Passo a passo

1. Selecione a pasta que contém os arquivos.
2. Configure uma ou mais regras. As regras são aplicadas nesta ordem: cortar caracteres, remover termos, substituir texto, normalizar espaços, acrescentar prefixo/sufixo e aplicar a capitalização escolhida.
3. Clique em **Pré-visualizar**. Linhas marcadas como **Conflito** precisam ser corrigidas antes de prosseguir.
4. Clique em **Renomear arquivos** e confirme a operação.
5. Para reverter o último lote, selecione a mesma pasta e clique em **Desfazer último lote**.

O atalho **Ctrl + Enter** abre a pré-visualização.

**Exemplo:** para converter 2024_relatorio final.pdf em Relatorio Final.pdf, use **Do início = 5** e **Capitalizar palavras**.

## Histórico e proteção contra conflitos

O histórico do último lote é guardado na pasta selecionada, no arquivo .renomeador_portable_historico.json. O programa exclui esse arquivo da lista de renomeação. Um novo lote bem-sucedido substitui o histórico anterior; portanto, só o lote mais recente pode ser desfeito.

Antes de renomear, o programa verifica destinos duplicados, nomes reservados do Windows e arquivos ou pastas que já ocupem o destino. A operação é feita em duas fases com nomes temporários para permitir trocas como a.txt para b.txt e b.txt para a.txt. Se uma etapa falhar, o programa tenta restaurar os nomes anteriores.

Evite mover, excluir ou renomear manualmente os arquivos entre a renomeação e a opção de desfazer. Como acontece com qualquer alteração de arquivos, mantenha cópias de segurança de dados importantes.

## Desenvolvimento e testes

A interface é feita com Tkinter; a lógica de arquivos fica em renamer.py. O projeto usa somente a biblioteca padrão do Python durante a execução.

Para rodar os testes, execute no PowerShell, a partir da pasta do projeto:

    py -m unittest discover -s tests -v

O GitHub Actions executa os testes e empacota o programa como um executável Windows de arquivo único. É possível publicar um Release com o EXE e o ZIP tanto ao enviar uma tag vMAJOR.MINOR.PATCH quanto pela opção manual descrita acima.

## Licença

Ainda não foi definida uma licença de redistribuição para este repositório.
