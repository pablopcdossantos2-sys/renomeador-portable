import tempfile
import unittest
from pathlib import Path

from renamer import (
    HISTORY_FILENAME,
    RenameOptions,
    apply_renames,
    create_plan,
    transform_filename,
    undo_last_renaming,
    validate_filename,
)


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
            "Projeto meu final  revisto.pdf".replace("  ", " "),
        )

    def test_case_insensitive_replacement(self):
        options = RenameOptions(
            replace_from="relatorio",
            replace_to="Resumo",
            ignore_case=True,
            case_mode="MAIÚSCULAS",
        )
        self.assertEqual(transform_filename("Relatorio mensal.docx", options), "RESUMO MENSAL.docx")

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
            plan = create_plan(folder, RenameOptions(replace_from="one ", replace_to=""))
            self.assertEqual(len(plan), 2)
            self.assertTrue(any(item.error for item in plan))

    def test_history_file_is_not_included_in_plan(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "notes.txt").write_text("x", encoding="utf-8")
            (folder / HISTORY_FILENAME).write_text("[]", encoding="utf-8")
            plan = create_plan(folder, RenameOptions(prefix="new-"))
            self.assertEqual([item.original for item in plan], ["notes.txt"])


if __name__ == "__main__":
    unittest.main()
