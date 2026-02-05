"""CLI command tests: create-zips."""

import zipfile
from unittest.mock import MagicMock, patch


class TestCreateZips:
    """Test the flask create-zips CLI command."""

    def test_creates_pdf_zip(self, tmp_path):
        """ZIP should contain all PDFs from PDF_DIR."""
        import app as app_module

        data_dir = tmp_path / "data"
        pdf_dir = data_dir / "pdfs"
        zip_dir = data_dir / "zips"
        pdf_dir.mkdir(parents=True)

        (pdf_dir / "report-a.pdf").write_bytes(b"%PDF-fake-a")
        (pdf_dir / "report-b.pdf").write_bytes(b"%PDF-fake-b")

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "PDF_DIR", pdf_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir):
            result = runner.invoke(args=["create-zips", "--no-texts"])

        assert result.exit_code == 0
        assert (zip_dir / "vsberichte.zip").exists()

        with zipfile.ZipFile(str(zip_dir / "vsberichte.zip"), "r") as zf:
            names = sorted(zf.namelist())
            assert names == ["report-a.pdf", "report-b.pdf"]

    def test_incremental_no_duplicates(self, tmp_path):
        """Running twice should not duplicate entries in the ZIP."""
        import app as app_module

        data_dir = tmp_path / "data"
        pdf_dir = data_dir / "pdfs"
        zip_dir = data_dir / "zips"
        pdf_dir.mkdir(parents=True)

        (pdf_dir / "report-a.pdf").write_bytes(b"%PDF-fake-a")

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "PDF_DIR", pdf_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir):
            runner.invoke(args=["create-zips", "--no-texts"])
            result = runner.invoke(args=["create-zips", "--no-texts"])

        assert result.exit_code == 0
        with zipfile.ZipFile(str(zip_dir / "vsberichte.zip"), "r") as zf:
            assert zf.namelist() == ["report-a.pdf"]

    def test_force_rebuilds(self, tmp_path):
        """--force should rebuild the ZIP from scratch."""
        import app as app_module

        data_dir = tmp_path / "data"
        pdf_dir = data_dir / "pdfs"
        zip_dir = data_dir / "zips"
        pdf_dir.mkdir(parents=True)

        (pdf_dir / "report-a.pdf").write_bytes(b"%PDF-fake-a")

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "PDF_DIR", pdf_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir):
            runner.invoke(args=["create-zips", "--no-texts"])
            # Remove the PDF so force rebuild produces an empty ZIP
            (pdf_dir / "report-a.pdf").unlink()
            result = runner.invoke(args=["create-zips", "--no-texts", "--force"])

        assert result.exit_code == 0
        with zipfile.ZipFile(str(zip_dir / "vsberichte.zip"), "r") as zf:
            assert zf.namelist() == []

    def test_text_zip_from_database(self, tmp_path):
        """Text ZIP should be built from database, not HTTP."""
        import app as app_module

        data_dir = tmp_path / "data"
        zip_dir = data_dir / "zips"

        mock_page1 = MagicMock()
        mock_page1.content = "Page 1 text"
        mock_page2 = MagicMock()
        mock_page2.content = "Page 2 text"

        mock_doc = MagicMock()
        mock_doc.jurisdiction = "Bund"
        mock_doc.year = 2020
        mock_doc.file_url = "/pdfs/vsb-bund-2020.pdf"
        mock_doc.pages = [mock_page1, mock_page2]

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with app_module.app.app_context(), \
             patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir), \
             patch.object(app_module.Document, "query") as mock_query:
            mock_query.order_by.return_value.all.return_value = [mock_doc]
            result = runner.invoke(args=["create-zips", "--no-pdfs"])

        assert result.exit_code == 0
        assert (zip_dir / "vsberichte-texts.zip").exists()

        with zipfile.ZipFile(str(zip_dir / "vsberichte-texts.zip"), "r") as zf:
            names = zf.namelist()
            assert "vsb-bund-2020.txt" in names
            content = zf.read("vsb-bund-2020.txt").decode("utf-8")
            assert "Page 1 text" in content
            assert "Page 2 text" in content

    def test_pdf_zip_removes_deleted_files(self, tmp_path):
        """Deleting a PDF on disk should remove it from the ZIP on rebuild."""
        import app as app_module

        data_dir = tmp_path / "data"
        pdf_dir = data_dir / "pdfs"
        zip_dir = data_dir / "zips"
        pdf_dir.mkdir(parents=True)

        (pdf_dir / "report-a.pdf").write_bytes(b"%PDF-fake-a")
        (pdf_dir / "report-b.pdf").write_bytes(b"%PDF-fake-b")

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "PDF_DIR", pdf_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir):
            runner.invoke(args=["create-zips", "--no-texts"])
            # Delete one PDF
            (pdf_dir / "report-b.pdf").unlink()
            result = runner.invoke(args=["create-zips", "--no-texts"])

        assert result.exit_code == 0
        with zipfile.ZipFile(str(zip_dir / "vsberichte.zip"), "r") as zf:
            assert sorted(zf.namelist()) == ["report-a.pdf"]

    def test_pdf_zip_updates_changed_files(self, tmp_path):
        """Changing a PDF on disk should update it in the ZIP on rebuild."""
        import app as app_module

        data_dir = tmp_path / "data"
        pdf_dir = data_dir / "pdfs"
        zip_dir = data_dir / "zips"
        pdf_dir.mkdir(parents=True)

        (pdf_dir / "report-a.pdf").write_bytes(b"%PDF-fake-a")

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "PDF_DIR", pdf_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir):
            runner.invoke(args=["create-zips", "--no-texts"])
            # Overwrite with different content (different size)
            (pdf_dir / "report-a.pdf").write_bytes(b"%PDF-fake-a-updated-content")
            result = runner.invoke(args=["create-zips", "--no-texts"])

        assert result.exit_code == 0
        with zipfile.ZipFile(str(zip_dir / "vsberichte.zip"), "r") as zf:
            assert zf.namelist() == ["report-a.pdf"]
            assert zf.read("report-a.pdf") == b"%PDF-fake-a-updated-content"

    def test_text_zip_unique_filenames(self, tmp_path):
        """Documents with same jurisdiction+year but different file_url get unique names."""
        import app as app_module

        data_dir = tmp_path / "data"
        zip_dir = data_dir / "zips"

        mock_doc1 = MagicMock()
        mock_doc1.jurisdiction = "Bayern"
        mock_doc1.year = 2020
        mock_doc1.file_url = "/pdfs/vsb-bayern-2020.pdf"
        mock_doc1.pages = [MagicMock(content="Doc 1 text")]

        mock_doc2 = MagicMock()
        mock_doc2.jurisdiction = "Bayern"
        mock_doc2.year = 2020
        mock_doc2.file_url = "/pdfs/vsb-bayern-2020-teil2.pdf"
        mock_doc2.pages = [MagicMock(content="Doc 2 text")]

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with app_module.app.app_context(), \
             patch.object(app_module, "DATA_DIR", data_dir), \
             patch.object(app_module, "ZIP_DIR", zip_dir), \
             patch.object(app_module.Document, "query") as mock_query:
            mock_query.order_by.return_value.all.return_value = [mock_doc1, mock_doc2]
            result = runner.invoke(args=["create-zips", "--no-pdfs"])

        assert result.exit_code == 0
        with zipfile.ZipFile(str(zip_dir / "vsberichte-texts.zip"), "r") as zf:
            names = sorted(zf.namelist())
            assert names == ["vsb-bayern-2020-teil2.txt", "vsb-bayern-2020.txt"]

    def test_download_route_unknown_404(self):
        """Requesting an unknown filename should return 404."""
        from app import app
        with app.test_client() as client:
            response = client.get("/downloads/evil.zip")
            assert response.status_code == 404
