import tempfile
import unittest
from pathlib import Path

from renamer import (
    HISTORY_FILENAME,
    RenameOptions,
    apply_renames,
    correct_spelling,
    create_plan,
    smart_title_case,
    transform_filename,
    undo_last_renaming,
    validate_filename,
)


class FakeChecker:
    def __init__(self, mapping):
        self.mapping = mapping

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

    def test_smart_portuguese_title_case_keeps_short_words_lowercase(self):
        options = RenameOptions(case_mode="Título inteligente (PT-BR)")
        self.assertEqual(
            transform_filename("o SENHOR DA CASA DE PEDRO.pdf", options),
            "O Senhor da Casa de Pedro.pdf",
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

    def test_spell_correction_is_not_applied_unless_enabled(self):
        options = RenameOptions(case_mode="Manter", spellcheck=False)
        self.assertEqual(transform_filename("relatorio.pdf", options), "relatorio.pdf")

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
