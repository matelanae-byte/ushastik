import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree
from zipfile import ZipFile

from engine import rename_speakers, save_result


WORD = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def document_text(path):
    with ZipFile(path) as archive:
        content_types = ElementTree.fromstring(archive.read("[Content_Types].xml"))
        relationships = ElementTree.fromstring(archive.read("_rels/.rels"))
        document = ElementTree.fromstring(archive.read("word/document.xml"))
    assert any(entry.get("PartName") == "/word/document.xml" for entry in content_types)
    assert any(entry.get("Target") == "word/document.xml" for entry in relationships)
    return [node.text or "" for node in document.findall(".//w:t", WORD)]


class WordExportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.output = Path(directory.name)

    def save(self, segments, *, split=False, turns=None):
        return save_result(Path("Совещание & план.mp4"), self.output, segments, 10,
                           "ru", split, 1, "test", turns=turns)

    def test_word_export_keeps_names_timestamps_and_unicode(self):
        folder = self.save([{"start": 1, "end": 2.5, "speaker": "speaker_1",
                             "text": "Привет <мир> & команда"}], turns=[])
        path = folder / "transcript.docx"
        self.assertTrue(path.is_file(), "Word document was not exported")
        before = document_text(path)
        self.assertIn("Файл: Совещание & план.mp4", before)
        self.assertTrue(any(line.startswith("[00:00:01.000 — 00:00:02.500]") and "Спикер 1: Привет <мир> & команда" in line
                            for line in before))
        original = json.loads((folder / "transcript.json").read_text(encoding="utf-8"))
        rename_speakers(folder, {"speaker_1": "Мария & Олег"})
        self.assertTrue(any("Мария & Олег: Привет <мир> & команда" in line
                            for line in document_text(path)))
        updated = json.loads((folder / "transcript.json").read_text(encoding="utf-8"))
        self.assertEqual(original["segments"], updated["segments"])
        for ext in ("txt", "srt"):
            self.assertIn("Мария & Олег", (folder / f"transcript.{ext}").read_text(encoding="utf-8-sig"))

    def test_regenerating_legacy_channel_result_creates_word_document(self):
        folder = self.save([{"start": 0, "end": 2, "channel": 2, "text": "Готово"}], split=True)
        path = folder / "transcript.docx"
        path.unlink(missing_ok=True)
        rename_speakers(folder, {"channel_1": "Анна", "channel_2": "Павел"})
        self.assertTrue(path.is_file(), "Existing transcript was not exported to Word")
        self.assertTrue(any("Павел: Готово" in line for line in document_text(path)))

    def test_silent_recording_has_readable_word_document(self):
        folder = self.save([])
        path = folder / "transcript.docx"
        self.assertTrue(path.is_file(), "Silent recording has no Word document")
        self.assertIn("Речь не распознана. Проверьте запись на слух.", document_text(path))
