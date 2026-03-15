"""Word position extraction and highlight box tests."""

import gzip
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestExtractWordPositions:
    """Test the extract_word_positions function."""

    def test_creates_gzipped_json_files(self, tmp_path):
        import app as app_module

        mock_word = {
            "text": "Verfassungsschutz",
            "x0": 100.0,
            "top": 200.0,
            "x1": 250.0,
            "bottom": 215.0,
        }
        mock_page = MagicMock()
        mock_page.width = 595.0
        mock_page.height = 842.0
        mock_page.extract_words.return_value = [mock_word]

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            with patch("app.pdfplumber") as mock_pdfplumber:
                mock_pdfplumber.open.return_value = mock_pdf
                app_module.extract_word_positions(Path("/fake/vsbericht-2020.pdf"))

        out_file = tmp_path / "vsbericht-2020_0.json.gz"
        assert out_file.exists()

        with gzip.open(out_file, "rt", encoding="utf-8") as f:
            data = json.loads(f.read())

        assert data["page_width"] == 595.0
        assert data["page_height"] == 842.0
        assert len(data["words"]) == 1
        word = data["words"][0]
        assert word["t"] == "Verfassungsschutz"
        assert 0.0 <= word["x"] <= 1.0
        assert 0.0 <= word["y"] <= 1.0
        assert 0.0 <= word["w"] <= 1.0
        assert 0.0 <= word["h"] <= 1.0

    def test_normalized_coordinates(self, tmp_path):
        import app as app_module

        mock_word = {
            "text": "Test",
            "x0": 0.0,
            "top": 0.0,
            "x1": 595.0,
            "bottom": 842.0,
        }
        mock_page = MagicMock()
        mock_page.width = 595.0
        mock_page.height = 842.0
        mock_page.extract_words.return_value = [mock_word]

        mock_pdf = MagicMock()
        mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            with patch("app.pdfplumber") as mock_pdfplumber:
                mock_pdfplumber.open.return_value = mock_pdf
                app_module.extract_word_positions(Path("/fake/test.pdf"))

        with gzip.open(tmp_path / "test_0.json.gz", "rt") as f:
            data = json.loads(f.read())

        word = data["words"][0]
        assert word["x"] == 0.0
        assert word["y"] == 0.0
        assert word["w"] == 1.0
        assert word["h"] == 1.0


class TestGetHighlightBoxes:
    """Test the get_highlight_boxes function."""

    def _create_wordpos_file(self, tmp_path, filename, words):
        data = {
            "page_width": 595.0,
            "page_height": 842.0,
            "words": [
                {"t": w, "x": 0.1 * i, "y": 0.5, "w": 0.08, "h": 0.015}
                for i, w in enumerate(words)
            ],
        }
        with gzip.open(tmp_path / filename, "wt", encoding="utf-8") as f:
            json.dump(data, f)

    def test_returns_matching_boxes(self, tmp_path):
        import app as app_module

        self._create_wordpos_file(
            tmp_path, "vsbericht-2020_5.json.gz", ["Gernot", "Mörig", "aus", "Berlin"]
        )

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            boxes = app_module.get_highlight_boxes(
                "/images/vsbericht-2020_5.jpg", ["gernot", "mörig"]
            )

        assert len(boxes) == 2
        assert all("x" in b and "y" in b and "w" in b and "h" in b for b in boxes)

    def test_case_insensitive_matching(self, tmp_path):
        import app as app_module

        self._create_wordpos_file(
            tmp_path, "test_0.json.gz", ["MÖRIG", "Gernot", "test"]
        )

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            boxes = app_module.get_highlight_boxes(
                "/images/test_0.jpg", ["mörig", "gernot"]
            )

        assert len(boxes) == 2

    def test_substring_matching(self, tmp_path):
        import app as app_module

        self._create_wordpos_file(
            tmp_path, "test_0.json.gz", ["Verfassungsschutzbericht"]
        )

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            boxes = app_module.get_highlight_boxes(
                "/images/test_0.jpg", ["verfassungsschutz"]
            )

        assert len(boxes) == 1

    def test_missing_file_returns_empty(self, tmp_path):
        import app as app_module

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            boxes = app_module.get_highlight_boxes(
                "/images/nonexistent_0.jpg", ["test"]
            )

        assert boxes == []

    def test_limit_50_boxes(self, tmp_path):
        import app as app_module

        words = ["match"] * 60
        self._create_wordpos_file(tmp_path, "test_0.json.gz", words)

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            boxes = app_module.get_highlight_boxes("/images/test_0.jpg", ["match"])

        assert len(boxes) == 50

    def test_no_duplicate_boxes_for_multi_token_match(self, tmp_path):
        import app as app_module

        self._create_wordpos_file(tmp_path, "test_0.json.gz", ["testword"])

        with patch.object(app_module, "WORDPOS_DIR", tmp_path):
            boxes = app_module.get_highlight_boxes(
                "/images/test_0.jpg", ["test", "word"]
            )

        # "testword" matches both tokens but should only produce 1 box
        assert len(boxes) == 1


class TestExtractWordposCli:
    """Test the extract-wordpos CLI command."""

    def test_skips_english_kurzfassung_and_parl_files(self, tmp_path):
        import app as app_module

        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "vsbericht-2020_en.pdf").touch()
        (pdf_dir / "vsbericht-2020kurzfassung.pdf").touch()
        (pdf_dir / "vsbericht-2020_parl.pdf").touch()

        runner = app_module.app.test_cli_runner(mix_stderr=False)

        with patch.object(app_module, "PDF_DIR", pdf_dir):
            with patch.object(app_module, "WORDPOS_DIR", tmp_path / "wordpos"):
                with patch("app.extract_word_positions") as mock_extract:
                    runner.invoke(args=["extract-wordpos", "*"])

        mock_extract.assert_not_called()

    def test_skips_existing_without_force(self, tmp_path):
        import app as app_module

        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "vsbericht-2020.pdf").touch()

        wordpos_dir = tmp_path / "wordpos"
        wordpos_dir.mkdir()
        (wordpos_dir / "vsbericht-2020_0.json.gz").touch()

        runner = app_module.app.test_cli_runner(mix_stderr=False)

        with patch.object(app_module, "PDF_DIR", pdf_dir):
            with patch.object(app_module, "WORDPOS_DIR", wordpos_dir):
                with patch("app.extract_word_positions") as mock_extract:
                    runner.invoke(args=["extract-wordpos", "*"])

        mock_extract.assert_not_called()

    def test_extracts_new_pdfs(self, tmp_path):
        import app as app_module

        pdf_dir = tmp_path / "pdfs"
        pdf_dir.mkdir()
        (pdf_dir / "vsbericht-2020.pdf").touch()

        wordpos_dir = tmp_path / "wordpos"

        runner = app_module.app.test_cli_runner(mix_stderr=False)

        with patch.object(app_module, "PDF_DIR", pdf_dir):
            with patch.object(app_module, "WORDPOS_DIR", wordpos_dir):
                with patch("app.extract_word_positions") as mock_extract:
                    runner.invoke(args=["extract-wordpos", "*"])

        mock_extract.assert_called_once()
