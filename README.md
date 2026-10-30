# Renomeador Portátil

Aplicativo portátil para Windows que renomeia arquivos e pastas em lote, com pré-visualização, seleção individual dos itens, temas claro/escuro e opção de desfazer o último lote.

## Funcionalidades

- Renomeia arquivos, pastas e subpastas, incluindo os arquivos dentro delas.
- Permite incluir ou limitar a análise aos itens diretamente dentro da pasta escolhida.
- Permite marcar/desmarcar na prévia os itens que deseja renomear, com ações de seleção em lote, inversão, filtros e ordenação por coluna.
- Oferece menu de contexto na prévia para copiar caminhos, comparar nomes e abrir a pasta do item.
- Mostra quantas regras estão ativas e permite limpar todas de uma vez.
- Mostra o caminho atual e o caminho proposto, o tipo do item e os conflitos antes de executar.
- Abre maximizado por padrão no Windows.
- Alterna entre os modos **Claro** e **Escuro**.
- Usa um ícone próprio nas janelas do aplicativo e no executável Windows.
- Remove uma quantidade de caracteres do início ou do final do nome, preservando a extensão dos arquivos.
- Remove vários termos, separados por vírgula, e substitui texto literalmente, com opção de ignorar maiúsculas/minúsculas. A substituição atua sobre o nome antes da extensão; espaços acidentais nas extremidades do texto buscado são desconsiderados quando o termo contém outros caracteres; um espaço digitado isoladamente pode ser usado para substituir espaços entre palavras.
- Adiciona prefixos e sufixos.
- Por padrão, mantém os nomes originais. Quando solicitado, converte nomes para MAIÚSCULAS, minúsculas ou aplica capitalização inteligente em português, inglês ou nos dois idiomas.
- Corrige ortografia opcionalmente com dicionário português, inglês ou ambos ao mesmo tempo; combina vocabulários suplementares e preserva termos reconhecidos em qualquer idioma. Também permite adicionar palavras personalizadas.
- Detecta nomes inválidos, destinos ocupados e colisões de caminhos.
- Permite desfazer o último lote bem-sucedido, desde que os itens ainda estejam nos caminhos esperados.

Extensões compostas conhecidas, como `.tar.gz`, `.tar.bz2`, `.tar.xz`, `.tar.zst` e `.user.js`, também são preservadas. A extensão dos arquivos é preservada. Links simbólicos e junctions do Windows não são seguidos nem renomeados; seus próprios nomes continuam sendo considerados ocupados para evitar colisões. O programa não altera a pasta raiz que foi escolhida como destino, mas pode renomear pastas e subpastas que aparecem na pré-visualização.

## Como usar no Windows

### Opção 1 — Executável portátil

1. Abra a aba **Actions** deste repositório.
2. Entre na execução mais recente bem-sucedida do fluxo **Testes e executável Windows**.
3. Na seção **Artifacts**, baixe **RenomeadorPortable-Windows**.
4. Extraia o ZIP e abra **RenomeadorPortable.exe**.

O executável inclui o ícone e os dicionários locais e não exige Python instalado ou instalação tradicional. O Windows pode exibir um aviso de segurança para programas baixados da internet; confira se o arquivo veio deste repositório antes de optar por executá-lo.

Para publicar uma versão sem instalar Git no computador: abra **Actions → Testes e executável Windows → Run workflow**, selecione a branch **main** e informe uma versão como **v0.1.0** no campo de versão. Deixe o campo vazio para apenas gerar o executável. Após a execução bem-sucedida, a versão será publicada em **Releases** com o EXE e o ZIP.

### Opção 2 — Executar o código-fonte

É necessário ter Python 3.10 ou mais recente instalado com o componente **Tkinter**.

1. Baixe o repositório pelo botão **Code → Download ZIP** e extraia os arquivos.
2. Abra um terminal nessa pasta e instale as dependências:

    py -m pip install -r requirements.txt

3. Execute:

    py main.py

O script gera os arquivos PNG/ICO do ícone na primeira inicialização. Se o Pillow não estiver disponível, a interface ainda abre, mas a geração/visualização do ícone poderá não funcionar.

## Passo a passo

1. Selecione a pasta que servirá de raiz para a análise.
2. Deixe **Incluir subpastas e arquivos dentro delas** marcado para analisar a árvore inteira. Desmarque para limitar a análise ao conteúdo diretamente dentro da pasta raiz.
3. Configure as regras. Em **Substituir texto**, informe o trecho em **De** e o novo conteúdo em **Para**; a extensão do arquivo é mantida. O texto buscado não diferencia maiúsculas/minúsculas somente quando a opção correspondente estiver marcada. As regras são aplicadas ao nome de cada arquivo/pasta; os caminhos dos descendentes acompanham automaticamente as pastas selecionadas que forem renomeadas.
4. Clique em **Pré-visualizar**. Use a caixa da primeira coluna para marcar ou desmarcar itens individuais. Clique nos títulos das colunas para ordenar a prévia; clique novamente para inverter a ordem. Clique com o botão direito em uma linha para copiar os caminhos, comparar o nome atual com o proposto ou abrir a pasta correspondente. Use **Limpar regras** para voltar às configurações neutras sem mudar a pasta selecionada. **Selecionar alterações**, **Desmarcar tudo** e **Inverter seleção** ajudam a selecionar vários itens.
5. Use a busca e o filtro para localizar itens, pastas, arquivos, conflitos ou alterações propostas.
6. Confira a coluna **Situação**. Nenhum item será renomeado quando houver conflitos no plano atual; resolva-os primeiro.
7. Clique em **Renomear selecionados** e confirme a operação.
8. Para reverter o lote mais recente, selecione a mesma pasta e clique em **Desfazer último lote**.

O atalho **Ctrl + Enter** abre a pré-visualização. A preferência de tema e a última pasta utilizada são salvas em `%APPDATA%\\RenomeadorPortatil\\config.json`; se não houver tema salvo, o programa tenta acompanhar o tema de aplicativos do Windows. Sem regras ativas, a prévia mantém os nomes originais e não marca arquivos para renomeação. Para marcar/desmarcar a linha selecionada, clique na caixa de seleção ou pressione a barra de espaço quando a tabela estiver focada.

**Como a seleção de pastas funciona:** marcar uma pasta para renomear também muda o caminho de seus conteúdos, como aconteceria no Explorador de Arquivos. Isso não renomeia automaticamente o nome-base dos arquivos que estão dentro dela. Para alterar o próprio nome de um arquivo, marque também a linha dele. Se desmarcar a pasta, mas mantiver um arquivo selecionado, o arquivo é renomeado dentro do nome atual da pasta.

## Capitalização inteligente e dicionários

O modo **Capitalizar todas as palavras** coloca a inicial de cada palavra em maiúscula, sem exceções. O modo legado **Capitalizar palavras** continua aceito internamente para compatibilidade, mas não é exibido na interface. O modo **Título inteligente (PT-BR/EN)** combina as listas de conectivos dos dois idiomas para nomes que misturam português e inglês.

O modo **Título inteligente (PT-BR)** mantém conectivos como *a, as, o, os, um, uma, de, da, das, do, dos, e, em, por, para, com, sem, no, na, nos, nas, ao, à, às* e *pelo* em minúsculas no meio do título, exceto no início do nome.

O modo **Title Case (English)** aplica uma regra equivalente aos conectivos ingleses, como *a, an, the, and, but, or, as, at, by, for, in, of, on, to, from, with* e *without*. Siglas comuns como PDF, API, HTML e NASA são preservadas.

A correção ortográfica usa o dicionário da biblioteca **pyspellchecker** e vocabulários suplementares do projeto em **assets/dictionary_pt_br.txt** e **assets/dictionary_en.txt**. Na lista **Dicionário(s) de correção**, escolha **Português (Brasil)**, **English** ou **Português + English**. A opção combinada carrega os dois dicionários simultaneamente, para títulos que misturam português e inglês. Palavras reconhecidas em qualquer um dos idiomas são preservadas. O vocabulário PT-BR inclui formas brasileiras e termos de informática/documentos; o inglês inclui termos de arquivos, pastas, interface e uso técnico. Também é possível informar palavras personalizadas, separadas por vírgula, para que sejam preservadas pelo corretor.

A correção é **opcional, local e baseada em palavras**, não uma revisão gramatical. Ela pode sugerir palavras erradas no lugar de nomes próprios, marcas, modelos, siglas não reconhecidas ou termos técnicos. O dicionário português é suplementar ao dicionário português geral; não é uma edição completa e separada exclusivamente de PT-BR. Confira sempre a pré-visualização antes de executar um lote.

## Histórico, conflitos e segurança

O histórico do último lote fica no arquivo **.renomeador_portable_historico.json**, dentro da pasta raiz selecionada. Um novo lote bem-sucedido substitui o histórico anterior; portanto, só a última operação pode ser desfeita.

O programa verifica os caminhos de destino levando em conta renomeações de diretórios e descendentes. As operações são feitas por grupos, começando pelos níveis mais profundos e usando nomes temporários para suportar trocas sem sobrescrever arquivos. Se uma etapa falhar, o programa tenta restaurar os nomes anteriores.

Evite mover, excluir ou renomear manualmente os itens entre a operação e a opção de desfazer. Como acontece com qualquer alteração de arquivos, mantenha cópias de segurança de dados importantes.

## Desenvolvimento e testes

A interface é feita com Tkinter em **main.py**. A lógica de renomeação e as verificações de caminhos estão em **renamer.py**; **theme.py** centraliza as paletas e **config.py** cuida das preferências locais. As dependências são declaradas em **requirements.txt**; o GitHub Actions verifica a sintaxe, executa os testes e compila o executável Windows incluindo ícone e dicionários.

Para executar os testes no PowerShell:

    py -m unittest discover -s tests -v

A compilação gera um EXE com ícone próprio, além de um ZIP. O workflow também pode publicar um Release via **Run workflow**, sem exigir Git instalado no computador.

## Licença

Este projeto é distribuído sob os termos da **GNU Affero General Public License v3.0 (AGPL-3.0)**. Consulte o arquivo [LICENSE](LICENSE) para o texto integral.
