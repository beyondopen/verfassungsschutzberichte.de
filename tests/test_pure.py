"""Pure-function tests (no Flask/DB required)."""

from collections import Counter
from unittest.mock import MagicMock


class TestCountTokens:
    """Test the count_tokens helper function."""

    def test_single_text(self):
        from app import count_tokens
        result = count_tokens(["hello world"])
        assert isinstance(result, Counter)
        assert result["hello"] == 1
        assert result["world"] == 1

    def test_multiple_texts(self):
        from app import count_tokens
        result = count_tokens(["hello world", "hello again"])
        assert result["hello"] == 2

    def test_empty_input(self):
        from app import count_tokens
        result = count_tokens([])
        assert len(result) == 0


class TestSpecialPdfPreproc:
    """Test the special_pdf_preproc helper function."""

    def test_joins_hyphenated_words(self):
        from app import special_pdf_preproc
        # Hyphen followed by whitespace between word parts should be joined
        assert special_pdf_preproc("Verfassungs- schutz") == "Verfassungsschutz"

    def test_preserves_normal_hyphens(self):
        from app import special_pdf_preproc
        # Hyphens not followed by whitespace should stay
        assert special_pdf_preproc("Baden-Württemberg") == "Baden-Württemberg"

    def test_preserves_plain_text(self):
        from app import special_pdf_preproc
        assert special_pdf_preproc("hello world") == "hello world"


class TestSerializeDoc:
    """Test the serialize_doc helper function."""

    def test_serialize_doc_fields(self):
        from app import serialize_doc
        mock_doc = MagicMock()
        mock_doc.year = 2020
        mock_doc.title = "Verfassungsschutzbericht 2020"
        mock_doc.jurisdiction = "Bund"
        mock_doc.file_url = "/pdfs/test-bund-2020.pdf"
        mock_doc.num_pages = 10

        result = serialize_doc(mock_doc)
        assert result["year"] == 2020
        assert result["title"] == "Verfassungsschutzbericht 2020"
        assert result["jurisdiction"] == "Bund"
        assert result["file_url"] == "https://verfassungsschutzberichte.de/pdfs/test-bund-2020.pdf"
        assert result["num_pages"] == 10
