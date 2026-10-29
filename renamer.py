"""Lógica de renomeação para arquivos e diretórios, com histórico reversível."""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Iterable

HISTORY_FILENAME = ".renomeador_portable_historico.json"
_TEMP_HISTORY_PREFIX = HISTORY_FILENAME + "."

# Vocabulário suplementar útil para português brasileiro, documentos e informática.
PT_BR_EXTRA_WORDS = {
    "ações", "análise", "análises", "aplicativo", "aplicativos", "arquivamento",
    "arquivamentos", "arquivo", "arquivos", "atalho", "atalhos", "áudio", "áudios",
    "autônomo", "autônomos", "brasileira", "brasileiras", "brasileiro", "brasileiros",
    "cabeçalho", "cabeçalhos", "capitalização", "caractere", "caracteres", "cópia",
    "cópias", "corretor", "corretores", "correção", "dicionário", "dicionários",
    "diretório", "diretórios", "documentação", "documentações", "documento", "documentos",
    "edição", "edições", "endereço", "endereços", "extensão", "extensões", "ferramenta",
    "ferramentas", "formatação", "histórico", "históricos", "ícone", "ícones",
    "imagem", "imagens", "informática", "maiúscula", "maiúsculas", "minúscula",
    "minúsculas", "ortográfica", "ortográficas", "ortográfico", "ortográficos",
    "palavra", "palavras", "parâmetro", "parâmetros", "prévia", "pré-visualização",
    "prefixo", "prefixos", "programa", "programas", "público", "públicos",
    "renomeação", "renomeações", "renomear", "renomeado", "renomeados", "renomeador",
    "renomeadores", "relatório", "relatórios", "reutilizável", "seleção", "seleções",
    "subpasta", "subpastas", "sufixo", "sufixos", "usuário", "usuários", "válida",
    "válidas", "válido", "válidos", "vocabulário", "planilha", "planilhas",
    "apresentação", "apresentações", "configuração", "configurações",
}
EN_EXTRA_WORDS = {
    "app", "apps", "archive", "archives", "backup", "backups", "batch", "batches",
    "bookmark", "bookmarks", "capitalization", "checkbox", "checkboxes", "configurable",
    "configuration", "configurations", "dictionary", "dictionaries", "directory",
    "directories", "document", "documents", "download", "downloads", "dragging",
    "filename", "filenames", "filepath", "filepaths", "filesystem", "folder", "folders",
    "formatting", "history", "histories", "icon", "icons", "lowercase", "metadata",
    "multilingual", "pathname", "pathnames", "preview", "previews", "renamable",
    "rename", "renamed", "renamer", "renamers", "renaming", "shortcut", "shortcuts",
    "spellcheck", "spellchecker", "spelling", "subdirectory", "subdirectories",
    "subfolder", "subfolders", "suffix", "suffixes", "thumbnail", "thumbnails",
    "timestamp", "timestamps", "toolbar", "toolbars", "uppercase", "undoable",
    "workflows", "spreadsheet", "spreadsheets", "presentation", "presentations",
}

PORTUGUESE_SMALL_WORDS = {
    "a", "as", "o", "os", "um", "uns", "uma", "umas",
    "de", "da", "das", "do", "dos", "e", "em", "no", "na", "nos", "nas",
    "num", "numa", "nuns", "numas", "dum", "duma", "duns", "dumas",
    "ao", "aos", "à", "às", "pelo", "pela", "pelos", "pelas",
    "por", "para", "com", "sem", "sob", "sobre", "entre", "até",
    "após", "perante", "contra", "desde", "durante", "que", "se",
}
ENGLISH_SMALL_WORDS = {
    "a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet",
    "as", "at", "by", "to", "of", "in", "on", "up", "off", "out",
    "over", "under", "after", "before", "between", "into", "through",
    "during", "without", "within", "with", "from", "about", "around",
    "against", "among", "along", "across", "behind", "below", "beneath",
    "beside", "beyond", "near", "past", "since", "until", "via", "per",
}
_WORD_RE = re.compile(r"[^\W\d_]+", flags=re.UNICODE)
_KNOWN_ACRONYMS = {
    "AI", "API", "CPU", "CSS", "CSV", "DVD", "GPS", "GPU", "HDMI",
    "HTML", "HTTP", "HTTPS", "IBM", "NASA", "PDF", "PC", "RAM",
    "SQL", "SSD", "USB", "URL", "WWW", "XML", "ZIP",
}


@dataclass
class RenameOptions:
    remove_start: int = 0
    remove_end: int = 0
    remove_terms: list[str] = field(default_factory=list)
    replace_from: str = ""
    replace_to: str = ""
    prefix: str = ""
    suffix: str = ""
    case_mode: str = "Manter"
    ignore_case: bool = False
    spellcheck: bool = False
    spell_language: str = "Português (Brasil)"
    custom_words: list[str] = field(default_factory=list)


@dataclass
class RenameItem:
    original: str
    proposed: str
    status: str = "Pronto"
    error: str = ""
    relative_path: str = ""
    is_directory: bool = False
    selected: bool = False
    target_path: str = ""

    @property
    def changed(self) -> bool:
        """Indica se as regras mudam o nome-base deste item."""
        return self.original != self.proposed

    @property
    def path_changed(self) -> bool:
        """Indica se o caminho completo mudará, inclusive por renomeação ancestral."""
        return bool(self.target_path and self.target_path != self.relative_path)


def validate_filename(filename: str) -> str | None:
    """Retorna uma explicação se o nome não for válido no Windows."""
    if not filename or filename in {".", ".."}:
        return "O nome resultante está vazio."
    if filename != filename.strip() or filename.endswith("."):
        return "O nome não pode terminar com espaço ou ponto."
    if any(ord(char) < 32 for char in filename) or re.search(r'[<>:"/\\|?*]', filename):
        return 'O nome contém caracteres não permitidos pelo Windows: < > : " / \\ | ? *'
    if len(filename) > 255:
        return "O nome excede o limite de 255 caracteres."
    device_name = filename.split(".", 1)[0].rstrip(" .").upper()
    if re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])", device_name):
        return f'"{device_name}" é um nome reservado pelo Windows.'
    return None


def smart_title_case(text: str, language: str = "pt-BR") -> str:
    """Aplica capitalização de títulos, deixando conectivos em minúsculas."""
    code = language.lower()
    small_words = ENGLISH_SMALL_WORDS if code in {"en", "en-us", "english", "inglês", "ingles"} else PORTUGUESE_SMALL_WORDS
    output: list[str] = []
    cursor = 0
    first_word = True

    for match in _WORD_RE.finditer(text):
        output.append(text[cursor:match.start()])
        word = match.group()
        lower_word = word.lower()
        if word.isupper() and word in _KNOWN_ACRONYMS:
            replacement = word
        elif not first_word and lower_word in small_words:
            replacement = lower_word
        else:
            replacement = lower_word[:1].upper() + lower_word[1:]
        output.append(replacement)
        cursor = match.end()
        first_word = False

    output.append(text[cursor:])
    return "".join(output)


@lru_cache(maxsize=16)
def _get_spellchecker(language: str, extra_words: tuple[str, ...] = ()):
    """Carrega e reutiliza dicionários locais com vocabulário suplementar."""
    try:
        from spellchecker import SpellChecker
    except ImportError as error:
        raise RuntimeError(
            "A correção ortográfica precisa do pacote pyspellchecker. "
            "Instale as dependências com: py -m pip install -r requirements.txt"
        ) from error

    normalized = language.strip().lower()
    is_english = normalized in {"en", "english", "inglês", "ingles"}
    code = "en" if is_english else "pt"
    checker = SpellChecker(language=code, distance=1)
    checker.word_frequency.load_words(EN_EXTRA_WORDS if is_english else PT_BR_EXTRA_WORDS)
    checker.word_frequency.load_words([word.lower() for word in extra_words if word.strip()])
    return checker


def correct_spelling(
    text: str,
    language: str = "Português (Brasil)",
    checker=None,
    extra_words: Iterable[str] = (),
) -> str:
    """Corrige ortografia comum localmente e tenta preservar a capitalização original.

    Nomes próprios, marcas, siglas e vocabulário específico podem não ser reconhecidos;
    por isso, a correção é opcional e seus resultados devem ser conferidos na prévia.
    """
    words = tuple(sorted({word.strip().lower() for word in extra_words if word.strip()}))
    if checker is None:
        checker = _get_spellchecker(language, words)

    def replace_word(match: re.Match[str]) -> str:
        word = match.group()
        if len(word) < 4:
            return word
        if word.isupper() or any(char.isupper() for char in word[1:]):
            return word

        suggestion = checker.correction(word.lower())
        if not suggestion or not suggestion.isalpha() or suggestion.lower() == word.lower():
            return word
        return suggestion[0].upper() + suggestion[1:].lower() if word[0].isupper() else suggestion.lower()

    return re.sub(r"[^\W\d_]{4,}", replace_word, text, flags=re.UNICODE)


def transform_filename(filename: str, options: RenameOptions, *, is_directory: bool = False) -> str:
    """Transforma o nome, mantendo a extensão dos arquivos e não das pastas."""
    if is_directory:
        stem, extension = filename, ""
    else:
        stem, extension = os.path.splitext(filename)

    if options.remove_start:
        stem = stem[options.remove_start:]
    if options.remove_end:
        stem = stem[:-options.remove_end] if options.remove_end < len(stem) else ""

    for term in options.remove_terms:
        term = term.strip()
        if not term:
            continue
        if options.ignore_case:
            stem = re.sub(re.escape(term), "", stem, flags=re.IGNORECASE)
        else:
            stem = stem.replace(term, "")

    if options.replace_from:
        if options.ignore_case:
            stem = re.sub(
                re.escape(options.replace_from),
                lambda _match: options.replace_to,
                stem,
                flags=re.IGNORECASE,
            )
        else:
            stem = stem.replace(options.replace_from, options.replace_to)

    stem = re.sub(r"\s+", " ", stem).strip()
    stem = options.prefix + stem
    if options.suffix:
        stem += options.suffix

    if options.spellcheck:
        stem = correct_spelling(stem, options.spell_language, extra_words=options.custom_words)
    stem = re.sub(r"\s+", " ", stem).strip()

    if options.case_mode == "MAIÚSCULAS":
        stem = stem.upper()
    elif options.case_mode == "minúsculas":
        stem = stem.lower()
    elif options.case_mode in {"Capitalizar palavras", "Título inteligente (PT-BR)", "Título inteligente (PT-BR/EN)"}:
        language = "en" if options.spell_language.lower() == "english" else "pt-BR"
        stem = smart_title_case(stem, language)
    elif options.case_mode == "Title Case (English)":
        stem = smart_title_case(stem, "en")

    stem = re.sub(r"\s+", " ", stem).strip()
    return stem + extension


def _is_internal_file(name: str) -> bool:
    return name == HISTORY_FILENAME or name.startswith(_TEMP_HISTORY_PREFIX)


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _path_for(root: Path, relative_path: str) -> Path:
    pure = PurePosixPath(relative_path)
    if pure.is_absolute() or not pure.parts or any(part in {"", ".", ".."} for part in pure.parts):
        raise ValueError(f"Caminho relativo inválido: {relative_path!r}")
    return root.joinpath(*pure.parts)


def _effective_target(item: RenameItem, by_path: dict[str, RenameItem]) -> str:
    parts = PurePosixPath(item.relative_path).parts
    result: list[str] = []
    for index, part in enumerate(parts):
        prefix = PurePosixPath(*parts[: index + 1]).as_posix()
        if index == len(parts) - 1:
            if item.selected and item.changed:
                result.append(item.proposed)
            else:
                result.append(part)
            continue
        ancestor = by_path.get(prefix)
        if ancestor and ancestor.is_directory and ancestor.selected and ancestor.changed:
            result.append(ancestor.proposed)
        else:
            result.append(part)
    return PurePosixPath(*result).as_posix()


def evaluate_plan(folder: str | os.PathLike[str], items: list[RenameItem]) -> list[RenameItem]:
    """Recalcula conflitos e destinos efetivos após a seleção ser alterada."""
    root = Path(folder)
    by_path = {item.relative_path: item for item in items}
    errors: dict[str, list[str]] = {}
    existing_entries: dict[str, str] = {}

    for path in root.rglob("*"):
        try:
            rel = _relative(path, root)
        except ValueError:
            continue
        existing_entries[rel.casefold()] = rel

    for item in items:
        item.error = ""
        item.target_path = _effective_target(item, by_path)
        item.status = "Sem alteração"

        if item.selected and item.changed:
            problem = validate_filename(item.proposed)
            if problem:
                errors.setdefault(item.relative_path, []).append(problem)
        for part in PurePosixPath(item.target_path).parts:
            problem = validate_filename(part)
            if problem:
                errors.setdefault(item.relative_path, []).append(problem)
                break

    target_groups: dict[str, list[RenameItem]] = {}
    for item in items:
        target_groups.setdefault(item.target_path.casefold(), []).append(item)
    for duplicates in target_groups.values():
        if len(duplicates) > 1:
            names = ", ".join(item.relative_path for item in duplicates)
            for item in duplicates:
                errors.setdefault(item.relative_path, []).append(
                    f"Mais de um item resultaria no mesmo caminho ({names})."
                )

    moving_sources = {
        item.relative_path.casefold()
        for item in items
        if item.target_path != item.relative_path
    }
    for item in items:
        target_key = item.target_path.casefold()
        if item.target_path != item.relative_path and target_key in existing_entries and target_key not in moving_sources:
            errors.setdefault(item.relative_path, []).append(
                f'O destino "{existing_entries[target_key]}" já existe e não será substituído.'
            )

    for item in items:
        if item.relative_path in errors:
            item.error = " ".join(dict.fromkeys(errors[item.relative_path]))
            item.status = "Conflito"
        elif item.target_path != item.relative_path:
            if item.selected and item.changed:
                item.status = "Pasta a renomear" if item.is_directory else "Arquivo a renomear"
            else:
                item.status = "Será movido com a pasta"
        elif item.changed and not item.selected:
            item.status = "Não selecionado"
        else:
            item.status = "Sem alteração"
    return items


def create_plan(folder: str | os.PathLike[str], options: RenameOptions) -> list[RenameItem]:
    """Monta a prévia recursiva de arquivos e pastas, sem seguir links simbólicos."""
    root = Path(folder)
    if not root.is_dir():
        raise ValueError("Selecione uma pasta válida.")

    candidates: list[tuple[Path, bool]] = []
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(current)
        dirnames[:] = sorted(
            name for name in dirnames
            if not _is_internal_file(name) and not (base / name).is_symlink()
        )
        for name in dirnames:
            path = base / name
            candidates.append((path, True))
        for name in sorted(filenames, key=str.casefold):
            path = base / name
            if _is_internal_file(name) or path.is_symlink():
                continue
            candidates.append((path, False))

    candidates.sort(key=lambda entry: (len(PurePosixPath(_relative(entry[0], root)).parts), _relative(entry[0], root).casefold()))
    items: list[RenameItem] = []
    for path, is_directory in candidates:
        rel = _relative(path, root)
        proposed = transform_filename(path.name, options, is_directory=is_directory)
        items.append(
            RenameItem(
                original=path.name,
                proposed=proposed,
                status="Pronto" if proposed != path.name else "Sem alteração",
                relative_path=rel,
                is_directory=is_directory,
                selected=proposed != path.name,
                target_path=rel,
            )
        )
    return evaluate_plan(root, items)


def _clean_recursive_moves(
    root: Path,
    moves: Iterable[tuple[str, str]],
) -> list[tuple[str, str]]:
    cleaned: list[tuple[str, str]] = []
    seen_sources: set[str] = set()
    targets: dict[tuple[str, str], str] = {}
    groups: dict[str, list[tuple[str, str]]] = {}

    for source, target_name in moves:
        if Path(target_name).name != target_name:
            raise ValueError("O destino deve ser somente um nome, sem caminhos.")
        source_path = _path_for(root, source)
        if _is_internal_file(source_path.name):
            raise ValueError("O histórico interno do programa não pode ser renomeado.")
        problem = validate_filename(target_name)
        if problem:
            raise ValueError(f'Nome de destino inválido para "{source}": {problem}')
        if source.casefold() in seen_sources:
            raise ValueError(f'A origem "{source}" foi informada mais de uma vez.')
        seen_sources.add(source.casefold())
        if source_path.is_symlink() or not (source_path.is_file() or source_path.is_dir()):
            raise ValueError(f'O arquivo ou diretório de origem não existe: "{source}".')
        parent_rel = PurePosixPath(source).parent.as_posix()
        if parent_rel == ".":
            parent_rel = ""
        if not (root / Path(*PurePosixPath(parent_rel).parts)).is_dir():
            raise ValueError(f'A pasta de origem não existe: "{parent_rel}".')
        target_key = (parent_rel.casefold(), target_name.casefold())
        if target_key in targets:
            raise ValueError(
                f'Dois itens resultariam no mesmo nome: "{targets[target_key]}" e "{target_name}".'
            )
        targets[target_key] = target_name
        groups.setdefault(parent_rel, []).append((source_path.name, target_name))
        cleaned.append((PurePosixPath(source).as_posix(), target_name))

    for parent_rel, group in groups.items():
        parent = root.joinpath(*PurePosixPath(parent_rel).parts) if parent_rel else root
        existing = {p.name.casefold(): p.name for p in parent.iterdir()}
        moving = {source.casefold() for source, target in group if source.casefold() != target.casefold()}
        for source, target in group:
            if target.casefold() in existing and target.casefold() not in moving and target.casefold() != source.casefold():
                raise ValueError(
                    f'O destino "{existing[target.casefold()]}" já existe em "{parent_rel or "."}".'
                )
    return cleaned


def _target_path_for_move(source: str, move_map: dict[str, str]) -> str:
    parts = PurePosixPath(source).parts
    target_parts: list[str] = []
    for index, part in enumerate(parts):
        source_prefix = PurePosixPath(*parts[: index + 1]).as_posix()
        target_parts.append(move_map.get(source_prefix, part))
    return PurePosixPath(*target_parts).as_posix()


def apply_recursive_renames(
    folder: str | os.PathLike[str],
    moves: Iterable[tuple[str, str]],
    *,
    save_history: bool = True,
) -> int:
    """Renomeia entradas por diretório, começando pelas mais profundas."""
    root = Path(folder)
    if not root.is_dir():
        raise ValueError("A pasta selecionada não existe mais.")
    cleaned = _clean_recursive_moves(root, moves)
    if not cleaned:
        return 0

    move_map = {source: target for source, target in cleaned}
    history = [
        {"OldPath": source, "NewPath": _target_path_for_move(source, move_map)}
        for source, _target in cleaned
    ]

    temporary_history: str | None = None
    history_path = root / HISTORY_FILENAME
    if save_history:
        descriptor, temporary_history = tempfile.mkstemp(
            prefix=_TEMP_HISTORY_PREFIX, suffix=".tmp", dir=root, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(history, stream, ensure_ascii=False, indent=2)
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.unlink(temporary_history)
            except OSError:
                pass
            raise

    groups: dict[str, list[tuple[str, str]]] = {}
    for source, target in cleaned:
        parent_rel = PurePosixPath(source).parent.as_posix()
        if parent_rel == ".":
            parent_rel = ""
        groups.setdefault(parent_rel, []).append((PurePosixPath(source).name, target))

    completed_groups: list[tuple[str, list[tuple[str, str]]]] = []
    try:
        ordered_groups = sorted(
            groups.items(),
            key=lambda group: (len(PurePosixPath(group[0]).parts) if group[0] else 0, group[0].casefold()),
            reverse=True,
        )
        for parent_rel, group in ordered_groups:
            parent = root.joinpath(*PurePosixPath(parent_rel).parts) if parent_rel else root
            _perform_moves(parent, group)
            completed_groups.append((parent_rel, group))

        if save_history and temporary_history:
            os.replace(temporary_history, history_path)
            temporary_history = None
    except Exception as error:
        rollback_errors: list[str] = []
        for parent_rel, group in reversed(completed_groups):
            parent = root.joinpath(*PurePosixPath(parent_rel).parts) if parent_rel else root
            try:
                _perform_moves(parent, [(target, source) for source, target in reversed(group)])
            except Exception as rollback_error:
                rollback_errors.append(str(rollback_error))
        if temporary_history:
            try:
                os.unlink(temporary_history)
            except OSError:
                pass
        detail = f"Falha ao renomear arquivos/pastas: {error}"
        if rollback_errors:
            detail += "\nTambém houve falha ao restaurar alguns nomes: " + " | ".join(rollback_errors)
        raise RuntimeError(detail) from error
    return len(cleaned)


def _is_internal_file(name: str) -> bool:
    return name == HISTORY_FILENAME or name.startswith(_TEMP_HISTORY_PREFIX)


def _validate_moves(root: Path, moves: Iterable[tuple[str, str]]) -> list[tuple[str, str]]:
    cleaned: list[tuple[str, str]] = []
    seen_sources: set[str] = set()
    for source, target in moves:
        if source == target:
            continue
        if Path(source).name != source or Path(target).name != target:
            raise ValueError("A operação contém um caminho de arquivo inválido.")
        if _is_internal_file(source):
            raise ValueError("O histórico interno do programa não pode ser renomeado.")
        target_error = validate_filename(target)
        if target_error:
            raise ValueError(f'Nome de destino inválido para "{source}": {target_error}')
        source_key = source.casefold()
        if source_key in seen_sources:
            raise ValueError(f'O arquivo de origem "{source}" foi informado mais de uma vez.')
        seen_sources.add(source_key)
        source_path = root / source
        if not source_path.is_file() or source_path.is_symlink():
            raise ValueError(f'O arquivo de origem não foi encontrado: "{source}".')
        cleaned.append((source, target))

    target_keys: dict[str, str] = {}
    for source, target in cleaned:
        key = target.casefold()
        if key in target_keys:
            raise ValueError(f'Dois arquivos seriam renomeados para "{target_keys[key]}" e "{target}".')
        target_keys[key] = target

    changing_sources = {source.casefold() for source, _target in cleaned}
    existing = {entry.name.casefold(): entry.name for entry in root.iterdir()}
    for source, target in cleaned:
        key = target.casefold()
        if key in existing and key not in changing_sources:
            raise ValueError(f'O destino "{existing[key]}" já existe. Nenhum arquivo foi renomeado.')
    return cleaned


def _perform_moves(root: Path, moves: list[tuple[str, str]]) -> None:
    """Executa renomeações em duas fases para suportar trocas de nomes."""
    staged: list[tuple[str, str, str]] = []
    completed: list[tuple[str, str, str]] = []
    for source, target in moves:
        temporary = f".__renomeador_tmp_{uuid.uuid4().hex}"
        while (root / temporary).exists():
            temporary = f".__renomeador_tmp_{uuid.uuid4().hex}"
        staged.append((source, target, temporary))

    try:
        for source, target, temporary in staged:
            os.rename(root / source, root / temporary)
        for source, target, temporary in staged:
            os.rename(root / temporary, root / target)
            completed.append((source, target, temporary))
    except Exception as error:
        rollback_errors: list[str] = []
        for source, target, temporary in reversed(completed):
            try:
                if (root / target).exists():
                    os.rename(root / target, root / temporary)
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        for source, _target, temporary in reversed(staged):
            try:
                if (root / temporary).exists():
                    os.rename(root / temporary, root / source)
            except OSError as rollback_error:
                rollback_errors.append(str(rollback_error))
        detail = f"Falha ao renomear os arquivos: {error}"
        if rollback_errors:
            detail += "\nTambém houve falha ao restaurar alguns nomes: " + " | ".join(rollback_errors)
        raise RuntimeError(detail) from error


def apply_renames(
    folder: str | os.PathLike[str],
    moves: Iterable[tuple[str, str]],
    *,
    save_history: bool = True,
) -> int:
    """Compatibilidade com operações antigas na raiz da pasta."""
    root = Path(folder)
    if not root.is_dir():
        raise ValueError("A pasta selecionada não existe mais.")
    cleaned = _validate_moves(root, moves)
    if not cleaned:
        return 0

    temporary_history: str | None = None
    history_path = root / HISTORY_FILENAME
    if save_history:
        descriptor, temporary_history = tempfile.mkstemp(
            prefix=_TEMP_HISTORY_PREFIX, suffix=".tmp", dir=root, text=True
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(
                    [{"NomeAntigo": old, "NomeNovo": new} for old, new in cleaned],
                    stream, ensure_ascii=False, indent=2,
                )
        except Exception:
            try:
                os.close(descriptor)
            except OSError:
                pass
            try:
                os.unlink(temporary_history)
            except OSError:
                pass
            raise

    try:
        _perform_moves(root, cleaned)
        if save_history and temporary_history:
            os.replace(temporary_history, history_path)
            temporary_history = None
    except Exception:
        if temporary_history:
            try:
                os.unlink(temporary_history)
            except OSError:
                pass
        raise
    return len(cleaned)


def undo_last_renaming(folder: str | os.PathLike[str]) -> tuple[int, str | None]:
    """Desfaz o último lote, inclusive lotes recursivos das versões atuais."""
    root = Path(folder)
    history_path = root / HISTORY_FILENAME
    if not root.is_dir():
        raise ValueError("Selecione uma pasta válida.")
    if not history_path.is_file():
        raise FileNotFoundError("Nenhum histórico de renomeação encontrado nesta pasta.")

    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Não foi possível ler o histórico: {error}") from error
    if not isinstance(data, list) or not data:
        raise ValueError("O histórico está vazio ou possui formato inválido.")

    if all(isinstance(item, dict) and isinstance(item.get("OldPath"), str) and isinstance(item.get("NewPath"), str) for item in data):
        moves = [
            (item["NewPath"], PurePosixPath(item["OldPath"]).name)
            for item in data
        ]
        count = apply_recursive_renames(root, moves, save_history=False)
    else:
        moves: list[tuple[str, str]] = []
        for item in data:
            if not isinstance(item, dict) or not isinstance(item.get("NomeAntigo"), str) or not isinstance(item.get("NomeNovo"), str):
                raise ValueError("O histórico contém uma entrada inválida.")
            moves.append((item["NomeNovo"], item["NomeAntigo"]))
        count = apply_renames(root, moves, save_history=False)

    warning = None
    try:
        history_path.unlink()
    except OSError as error:
        warning = f"Os nomes foram restaurados, mas não foi possível apagar o histórico: {error}"
    return count, warning
