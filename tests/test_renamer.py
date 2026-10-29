import tempfile
import unittest
from pathlib import Path

from renamer import (
    _get_spellchecker,
    HISTORY_FILENAME,
    RenameOptions,
    apply_renames,
    apply_recursive_renames,
    correct_spelling,
    create_plan,
    smart_title_case,
    transform_filename,
    undo_last_renaming,
    evaluate_plan,
    validate_filename,
)

from main import PALETTES, _frame_background_color


class PaletteRoleTests(unittest.TestCase):
    def test_header_role_maps_to_navy_for_both_themes(self):
        for theme in ("Escuro", "Claro"):
            with self.subTest(theme=theme):
                self.assertEqual(
                    _frame_background_color(PALETTES[theme], "header"),
                    PALETTES[theme]["navy"],
                )

    def test_accent_role_maps_to_blue(self):
        for theme in ("Escuro", "Claro"):
            with self.subTest(theme=theme):
                self.assertEqual(
                    _frame_background_color(PALETTES[theme], "accent"),
                    PALETTES[theme]["blue"],
                )

    def test_unknown_role_falls_back_to_app_background(self):
        palette = PALETTES["Escuro"]
        self.assertEqual(
            _frame_background_color(palette, "role-not-configured"),
            palette["app"],
        )


class FakeChecker:
    def __init__(self, mapping, known_words=()):
        self.mapping = mapping
        self.known_words = {word.lower() for word in known_words}

    def __contains__(self, word):
        return word.lower() in self.known_words

    def correction(self, word):
        return self.mapping.get(word, word)


class TransformTests(unittest.TestCase):
    def test_keeps_extension_and_applies_rules(self):
        options = RenameOptions(
            remove_start=3,
            remove_end=2,
            replace_from="draft",
            replace_to="final",
            prefix="Projeto ",
            suffix=" revisto",
        )
        self.assertEqual(
            transform_filename("ABC meu draft xx.pdf", options),
            "Projeto meu final revisto.pdf",
        )

    def test_case_insensitive_replacement(self):
        options = RenameOptions(
            replace_from="relatorio",
            replace_to="Resumo",
            ignore_case=True,
            case_mode="MAIÚSCULAS",
        )
        self.assertEqual(transform_filename("Relatorio mensal.docx", options), "RESUMO MENSAL.docx")

    def test_text_replacement_changes_filename_and_preserves_extension(self):
        options = RenameOptions(
            replace_from="draft",
            replace_to="final",
            case_mode="Manter",
        )
        self.assertEqual(
            transform_filename("Project draft notes.PDF", options),
            "Project final notes.PDF",
        )

    def test_text_replacement_trims_outer_spaces_from_search_term(self):
        options = RenameOptions(
            replace_from="  draft  ",
            replace_to="final",
            case_mode="Manter",
        )
        self.assertEqual(
            transform_filename("Project draft notes.pdf", options),
            "Project final notes.pdf",
        )

    def test_text_replacement_can_remove_match_when_destination_is_empty(self):
        options = RenameOptions(replace_from="_draft", replace_to="", case_mode="Manter")
        self.assertEqual(transform_filename("report_draft.pdf", options), "report.pdf")

    def test_text_replacement_is_literal_and_case_sensitive_by_default(self):
        options = RenameOptions(replace_from="a.c", replace_to="X", case_mode="Manter")
        self.assertEqual(transform_filename("a.c AC axc.pdf", options), "X AC axc.pdf")

    def test_smart_portuguese_title_case_keeps_short_words_lowercase(self):
        options = RenameOptions(case_mode="Título inteligente (PT-BR)")
        self.assertEqual(
            transform_filename("o SENHOR DA CASA DE PEDRO.pdf", options),
            "O Senhor da Casa de Pedro.pdf",
        )

    def test_explicit_portuguese_title_case_ignores_spellcheck_language(self):
        options = RenameOptions(
            case_mode="Título inteligente (PT-BR)",
            spell_language="English",
        )
        self.assertEqual(
            transform_filename("A CASA DE PEDRO.txt", options),
            "A Casa de Pedro.txt",
        )

    def test_legacy_title_case_uses_smart_portuguese_rules(self):
        options = RenameOptions(case_mode="Capitalizar palavras")
        self.assertEqual(
            transform_filename("a CASA E o jardim.txt", options),
            "A Casa e o Jardim.txt",
        )

    def test_smart_english_title_case_keeps_short_words_lowercase(self):
        options = RenameOptions(case_mode="Title Case (English)")
        self.assertEqual(
            transform_filename("the LORD OF the rings.txt", options),
            "The Lord of the Rings.txt",
        )

    def test_title_case_preserves_common_acronyms(self):
        self.assertEqual(smart_title_case("relatorio em PDF", "pt-BR"), "Relatorio em PDF")

    def test_optional_spell_correction_preserves_case_and_acronyms(self):
        checker = FakeChecker({"relatorio": "relatório", "recieve": "receive"})
        self.assertEqual(
            correct_spelling("relatorio Recieve API iPhone", checker=checker),
            "relatório Receive API iPhone",
        )

    def test_spell_correction_preserves_known_words_in_any_loaded_language(self):
        checker = FakeChecker({"folder": "folded"}, known_words={"folder"})
        self.assertEqual(correct_spelling("folder", checker=checker), "folder")

    def test_combined_dictionary_contains_portuguese_and_english_words(self):
        checker = _get_spellchecker("Português + English")
        self.assertIn("arquivo", checker)
        self.assertIn("computer", checker)

    def test_spell_correction_is_not_applied_unless_enabled(self):
        options = RenameOptions(case_mode="Manter", spellcheck=False)
        self.assertEqual(transform_filename("relatorio.pdf", options), "relatorio.pdf")


    def test_directory_names_do_not_preserve_dot_suffix_as_extension(self):
        options = RenameOptions(prefix="Novo ")
        self.assertEqual(
            transform_filename("projeto.final", options, is_directory=True),
            "Novo projeto.final",
        )

    def test_nonrecursive_plan_still_lists_first_level_folders(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "Folder"
            nested.mkdir()
            (nested / "child.txt").write_text("x", encoding="utf-8")
            (root / "root.txt").write_text("y", encoding="utf-8")
            plan = create_plan(root, RenameOptions(prefix="Novo "), recursive=False)
            paths = {item.relative_path for item in plan}
            self.assertIn("Folder", paths)
            self.assertIn("root.txt", paths)
            self.assertNotIn("Folder/child.txt", paths)

    def test_recursive_plan_includes_subfolders_and_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            nested = root / "Relatorios"
            nested.mkdir()
            (nested / "relatorio.txt").write_text("x", encoding="utf-8")
            plan = create_plan(root, RenameOptions(prefix="Novo "))
            paths = {item.relative_path for item in plan}
            self.assertIn("Relatorios", paths)
            self.assertIn("Relatorios/relatorio.txt", paths)

    def test_recursive_rename_directory_and_child_file_can_be_undone(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "Relatorios"
            folder.mkdir()
            (folder / "arquivo.txt").write_text("conteúdo", encoding="utf-8")

            count = apply_recursive_renames(
                root,
                [
                    ("Relatorios", "Documentos"),
                    ("Relatorios/arquivo.txt", "relatorio.txt"),
                ],
            )
            self.assertEqual(count, 2)
            self.assertTrue((root / "Documentos" / "relatorio.txt").is_file())

            undone, warning = undo_last_renaming(root)
            self.assertEqual(undone, 2)
            self.assertIsNone(warning)
            self.assertEqual(
                (root / "Relatorios" / "arquivo.txt").read_text(encoding="utf-8"),
                "conteúdo",
            )

    def test_unselected_directory_does_not_rename_but_selected_child_does(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / "Relatorios"
            folder.mkdir()
            (folder / "arquivo.txt").write_text("x", encoding="utf-8")
            items = create_plan(root, RenameOptions(prefix="Novo "))
            by_path = {item.relative_path: item for item in items}
            by_path["Relatorios"].selected = False
            evaluate_plan(root, items)
            selected_moves = [
                (item.relative_path, item.proposed)
                for item in items
                if item.selected and item.changed and not item.error
            ]
            apply_recursive_renames(root, selected_moves)
            self.assertTrue((root / "Relatorios" / "Novo arquivo.txt").is_file())
            self.assertFalse((root / "Novo Relatorios").exists())

    def test_validation_rejects_windows_reserved_names(self):
        self.assertIsNotNone(validate_filename("CON.txt"))
        self.assertIsNotNone(validate_filename("bad?.txt"))
        self.assertIsNone(validate_filename("relatorio final.pdf"))


class FileOperationTests(unittest.TestCase):
    def test_swap_and_undo_last_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "a.txt").write_text("conteúdo A", encoding="utf-8")
            (folder / "b.txt").write_text("conteúdo B", encoding="utf-8")

            count = apply_renames(folder, [("a.txt", "b.txt"), ("b.txt", "a.txt")])
            self.assertEqual(count, 2)
            self.assertEqual((folder / "a.txt").read_text(encoding="utf-8"), "conteúdo B")
            self.assertEqual((folder / "b.txt").read_text(encoding="utf-8"), "conteúdo A")
            self.assertTrue((folder / HISTORY_FILENAME).is_file())

            undone, warning = undo_last_renaming(folder)
            self.assertEqual(undone, 2)
            self.assertIsNone(warning)
            self.assertEqual((folder / "a.txt").read_text(encoding="utf-8"), "conteúdo A")
            self.assertEqual((folder / "b.txt").read_text(encoding="utf-8"), "conteúdo B")
            self.assertFalse((folder / HISTORY_FILENAME).exists())

    def test_existing_unchanged_destination_blocks_operation(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "a.txt").write_text("A", encoding="utf-8")
            (folder / "b.txt").write_text("B", encoding="utf-8")

            with self.assertRaises(ValueError):
                apply_renames(folder, [("a.txt", "b.txt")])
            self.assertEqual((folder / "a.txt").read_text(encoding="utf-8"), "A")
            self.assertEqual((folder / "b.txt").read_text(encoding="utf-8"), "B")

    def test_plan_reports_duplicate_destination(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "one photo.jpg").write_text("1", encoding="utf-8")
            (folder / "two photo.jpg").write_text("2", encoding="utf-8")
            plan = create_plan(folder, RenameOptions(remove_terms=["one ", "two "]))
            self.assertEqual(len(plan), 2)
            self.assertTrue(all(item.error for item in plan))

    def test_history_file_is_not_included_in_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "notes.txt").write_text("x", encoding="utf-8")
            (folder / HISTORY_FILENAME).write_text("[]", encoding="utf-8")
            plan = create_plan(folder, RenameOptions(prefix="new-"))
            self.assertEqual([item.original for item in plan], ["notes.txt"])


if __name__ == "__main__":
    unittest.main()
