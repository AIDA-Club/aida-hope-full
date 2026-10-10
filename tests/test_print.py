"""Printed materials: the draft_marks switch and the QR codes (built into a temporary folder)."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_print  # noqa: E402
import check_print  # noqa: E402


def build_all(folder: Path, draft_marks: bool) -> None:
    build_print.register_fonts()
    content, booth, predictions = build_print.load_inputs()
    content["draft_marks"] = draft_marks
    with patch.object(build_print, "OUT", folder):
        build_print.build_case_cards(content, booth)
        build_print.build_answer_key(content, booth)
        build_print.build_folders(content, predictions)
        build_print.build_tips_card(content)
        build_print.build_takehome(content)
        build_print.build_poster(content, booth)


class PrintTests(unittest.TestCase):
    def test_draft_marks_switch(self):
        for draft_marks in (False, True):
            with tempfile.TemporaryDirectory() as temporary:
                build_all(Path(temporary), draft_marks)
                marks = check_print.draft_marks(Path(temporary))
                self.assertEqual(len(marks), 6)
                if draft_marks:
                    for name in ("folders.pdf", "tips_card.pdf", "takehome_cards.pdf", "poster_A2.pdf",
                                 "case_cards.pdf"):
                        self.assertGreater(marks[name], 0, name)
                else:
                    self.assertEqual(sum(marks.values()), 0, marks)
                if not draft_marks:
                    ok, lines = check_print.check(Path(temporary))
                    self.assertTrue(ok, lines)

    def test_draft_marks_on_by_default(self):
        content, _, _ = build_print.load_inputs()
        self.assertIs(content["draft_marks"], True)

    def test_poster_qr_is_large(self):
        self.assertGreaterEqual(build_print.POSTER_QR_MM / 25.4 * 72, 260)


if __name__ == "__main__":
    unittest.main()
