"""Lógica de renomeação do Renomeador Portátil.

Não depende de Tkinter, permitindo testar a lógica sem abrir a interface.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

HISTORY_FILENAME = ".renomeador_portable_historico.json"
_TEMP_HISTORY_PREFIX = HISTORY_FILENAME + "."


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


@dataclass
class RenameItem:
    original: str
    proposed: str
    status: str = "Pronto"
    error: str = ""

    @property
    def changed(self) -> bool:
        return self.original != self.proposed


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

        # Preserva siglas comuns, sem deixar nomes inteiros em CAIXA ALTA assim.
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


@lru_cache(maxsize=2)
def _get_spellchecker(language: str):
    """Carrega uma única instância local por idioma."""
    try:
        from spellchecker import SpellChecker
    except ImportError as error:
        raise RuntimeError(
            "A correção ortográfica precisa do pacote pyspellchecker. "
            "Instale as dependências com: py -m pip install -r requirements.txt"
        ) from error

    normalized = language.strip().lower()
    code = "en" if normalized in {"en", "english", "inglês", "ingles"} else "pt"
    return SpellChecker(language=code, distance=1)


def correct_spelling(text: str, language: str = "Português (Brasil)", checker=None) -> str:
    """Corrige palavras de forma local, tentando preservar a capitalização original.

    Palavras curtas, siglas e tokens com capitalização interna são preservados.
    Nomes próprios podem ser confundidos com palavras comuns; por isso, o recurso
    é opcional e seus resultados devem ser conferidos na pré-visualização.
    """
    if checker is None:
        checker = _get_spellchecker(language)

    def replace_word(match: re.Match[str]) -> str:
        word = match.group()
        if len(word) < 4:
            return word
        if word.isupper() or (any(char.isupper() for char in word[1:])):
            return word

        suggestion = checker.correction(word.lower())
        if not suggestion or not suggestion.isalpha() or suggestion.lower() == word.lower():
            return word
        if word[0].isupper():
            return suggestion[0].upper() + suggestion[1:].lower()
        return suggestion.lower()

    return re.sub(r"[^\W\d_]{4,}", replace_word, text, flags=re.UNICODE)


def transform_filename(filename: str, options: RenameOptions) -> str:
    """Transforma o nome do arquivo, preservando sua extensão."""
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

    # A extensão não passa pela correção ortográfica nem pela capitalização.
    if options.spellcheck:
        stem = correct_spelling(stem, options.spell_language)
    stem = re.sub(r"\s+", " ", stem).strip()

    if options.case_mode == "MAIÚSCULAS":
        stem = stem.upper()
    elif options.case_mode == "minúsculas":
        stem = stem.lower()
    elif options.case_mode in {"Capitalizar palavras", "Título inteligente (PT-BR)"}:
        stem = smart_title_case(stem, "pt-BR")
    elif options.case_mode == "Title Case (English)":
        stem = smart_title_case(stem, "en")

    stem = re.sub(r"\s+", " ", stem).strip()
    return stem + extension


def _is_internal_file(name: str) -> bool:
    return name == HISTORY_FILENAME or name.startswith(_TEMP_HISTORY_PREFIX)


def create_plan(folder: str | os.PathLike[str], options: RenameOptions) -> list[RenameItem]:
    """Monta uma prévia e identifica nomes inválidos ou conflitos."""
    root = Path(folder)
    if not root.is_dir():
        raise ValueError("Selecione uma pasta válida.")

    entries = sorted(
        (entry for entry in root.iterdir()
         if entry.is_file() and not entry.is_symlink() and not _is_internal_file(entry.name)),
        key=lambda entry: (entry.name.casefold(), entry.name),
    )
    items = [
        RenameItem(
            original=entry.name,
            proposed=transform_filename(entry.name, options),
            status="Sem alteração" if transform_filename(entry.name, options) == entry.name else "Pronto",
        )
        for entry in entries
    ]

    errors: dict[str, list[str]] = {}
    changed = [item for item in items if item.changed]
    changing_sources = {item.original.casefold() for item in changed}
    existing_names = {entry.name.casefold(): entry.name for entry in root.iterdir()}

    for item in changed:
        error = validate_filename(item.proposed)
        if error:
            errors.setdefault(item.original, []).append(error)

    targets: dict[str, list[RenameItem]] = {}
    for item in changed:
        targets.setdefault(item.proposed.casefold(), []).append(item)
    for duplicates in targets.values():
        if len(duplicates) > 1:
            names = ", ".join(item.original for item in duplicates)
            for item in duplicates:
                errors.setdefault(item.original, []).append(
                    f"Mais de um arquivo resultaria no mesmo nome ({names})."
                )

    for item in changed:
        key = item.proposed.casefold()
        if key in existing_names and key not in changing_sources:
            errors.setdefault(item.original, []).append(
                f'O destino "{existing_names[key]}" já existe e não será renomeado.'
            )

    for item in changed:
        if item.original in errors:
            item.status = "Conflito"
            item.error = " ".join(errors[item.original])
    return items


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
            raise ValueError(
                f'Dois arquivos seriam renomeados para "{target_keys[key]}" e "{target}".'
            )
        target_keys[key] = target

    changing_sources = {source.casefold() for source, _target in cleaned}
    existing = {entry.name.casefold(): entry.name for entry in root.iterdir()}
    for source, target in cleaned:
        key = target.casefold()
        if key in existing and key not in changing_sources:
            raise ValueError(
                f'O destino "{existing[key]}" já existe. Nenhum arquivo foi renomeado.'
            )
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
    """Aplica as mudanças; o histórico só é publicado se a operação concluir."""
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
            prefix=_TEMP_HISTORY_PREFIX,
            suffix=".tmp",
            dir=root,
            text=True,
        )
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(
                    [{"NomeAntigo": old, "NomeNovo": new} for old, new in cleaned],
                    stream,
                    ensure_ascii=False,
                    indent=2,
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
    """Desfaz o último lote salvo. Retorna quantidade e possível aviso de limpeza."""
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
