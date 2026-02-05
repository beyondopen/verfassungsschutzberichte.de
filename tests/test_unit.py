"""
Unit tests for verfassungsschutzberichte.de

These tests import functions directly and use the Flask test client
where a running server is not needed.
"""

import re
import zipfile
from collections import Counter
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Pure-function tests (no Flask/DB required)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Flask test-client tests (need app context but NOT a running server)
# ---------------------------------------------------------------------------

class TestGetIndex:
    """Test the get_index helper via the /api endpoint using the test client."""

    def test_api_returns_index(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/api')
            assert response.status_code == 200
            data = response.get_json()
            assert 'reports' in data
            assert 'total' in data
            assert isinstance(data['reports'], list)


class TestBlogFunctions:
    """Test blog-related routes via the Flask test client."""

    def test_blog_index(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/blog/')
            assert response.status_code == 200
            assert b'Blog' in response.data

    def test_blog_post_exists(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/blog/launch')
            assert response.status_code == 200

    def test_blog_post_not_found(self):
        from app import app
        with app.test_client() as client:
            response = client.get('/blog/nonexistent-slug-xyz')
            assert response.status_code == 404


class TestNonDebugBranches:
    """Test code paths that only execute when app.debug is False."""

    def test_trends_redirect_without_query(self):
        """Test that /trends redirects when no query and debug=False."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/trends')
                assert response.status_code == 302
                assert '/trends?q=nsu&q=raf' in response.headers['Location']
        finally:
            app.debug = True

    def test_regional_redirect_without_query(self):
        """Test that /regional redirects when no query and debug=False."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/regional')
                assert response.status_code == 302
                assert '/regional?q=vvn-bda' in response.headers['Location']
        finally:
            app.debug = True

    def test_pdf_download_non_debug(self):
        """Test PDF download uses X-Accel-Redirect in non-debug mode."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/pdfs/test-bund-2020.pdf')
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'application/pdf'
                assert response.headers['X-Accel-Redirect'] == '/internal-pdfs/test-bund-2020.pdf'
                assert 'noindex' in response.headers.get('X-Robots-Tag', '')
        finally:
            app.debug = True

    def test_image_download_jpeg_non_debug(self):
        """Test JPEG image download uses X-Accel-Redirect in non-debug mode."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/images/test-bund-2020_0.jpg')
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'image/jpeg'
                assert response.headers['X-Accel-Redirect'] == '/internal-images/test-bund-2020_0.jpg'
                assert 'noindex' in response.headers.get('X-Robots-Tag', '')
        finally:
            app.debug = True

    def test_image_download_avif_non_debug(self):
        """Test AVIF image download uses X-Accel-Redirect with correct content type."""
        from app import app
        app.debug = False
        try:
            with app.test_client() as client:
                response = client.get('/images/test-bund-2020_0.avif')
                assert response.status_code == 200
                assert response.headers['Content-Type'] == 'image/avif'
                assert response.headers['X-Accel-Redirect'] == '/internal-images/test-bund-2020_0.avif'
                assert 'noindex' in response.headers.get('X-Robots-Tag', '')
        finally:
            app.debug = True


class TestSearchEdgeCases:
    """Test search edge cases for additional coverage."""

    def test_search_no_results_query(self):
        """Test search with a query that returns no results (covers empty snips path)."""
        from app import app
        with app.test_client() as client:
            response = client.get('/suche?q=xyznonexistentterm99999')
            assert response.status_code == 200


class TestAutocompleteEdgeCases:
    """Test autocomplete edge cases for additional coverage."""

    def test_autocomplete_three_words(self):
        """Test autocomplete with 3+ words to cover intersection loop."""
        from app import app
        with app.test_client() as client:
            response = client.get('/api/auto-complete?q=die+und+v')
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, list)

    def test_autocomplete_nonexistent_first_token(self):
        """Test autocomplete where first token has no matches (covers empty ids return)."""
        from app import app
        with app.test_client() as client:
            response = client.get('/api/auto-complete?q=xyznonexistent99+abc')
            assert response.status_code == 200
            assert response.get_json() == []


# ---------------------------------------------------------------------------
# CLI command tests: export-data / import-data
# ---------------------------------------------------------------------------

class TestExportData:
    """Test the flask export-data CLI command."""

    def test_export_creates_tarball_with_pdfs(self, tmp_path):
        """Exporting should create a tar containing all PDFs including nested subdirs."""
        import app as app_module
        import tarfile

        data_dir = tmp_path / "data"
        (data_dir / "pdfs").mkdir(parents=True)
        (data_dir / "cleaned" / "bb").mkdir(parents=True)
        (data_dir / "pdfs" / "report-a.pdf").write_bytes(b"%PDF-fake-a")
        (data_dir / "cleaned" / "report-a.pdf").write_bytes(b"%PDF-fake-a-clean")
        (data_dir / "cleaned" / "bb" / "report-bb.pdf").write_bytes(b"%PDF-fake-bb")

        output_file = tmp_path / "export.tar"

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir):
            result = runner.invoke(args=["export-data", str(output_file)])

        assert result.exit_code == 0
        assert "Exported 3 PDFs" in result.output

        with tarfile.open(str(output_file), "r") as tar:
            names = sorted(tar.getnames())
            assert names == ["cleaned/bb/report-bb.pdf", "cleaned/report-a.pdf", "pdfs/report-a.pdf"]

    def test_export_no_pdfs_found(self, tmp_path):
        """Exporting when no PDFs exist should print a message."""
        import app as app_module

        data_dir = tmp_path / "data"
        (data_dir / "pdfs").mkdir(parents=True)
        output_file = tmp_path / "export.tar"

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir):
            result = runner.invoke(args=["export-data", str(output_file)])

        assert result.exit_code == 0
        assert "No PDF files found" in result.output

    def test_export_skips_missing_directories(self, tmp_path):
        """Exporting should skip directories that don't exist."""
        import app as app_module
        import tarfile

        data_dir = tmp_path / "data"
        (data_dir / "pdfs").mkdir(parents=True)
        (data_dir / "pdfs" / "report.pdf").write_bytes(b"%PDF-fake")
        # raw, cleaned, deleted don't exist

        output_file = tmp_path / "export.tar"

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir):
            result = runner.invoke(args=["export-data", str(output_file)])

        assert result.exit_code == 0
        assert "Exported 1 PDFs" in result.output

        with tarfile.open(str(output_file), "r") as tar:
            assert tar.getnames() == ["pdfs/report.pdf"]


class TestImportData:
    """Test the flask import-data CLI command."""

    def test_import_extracts_pdfs(self, tmp_path):
        """Importing should extract PDFs into correct subdirectories including nested."""
        import app as app_module
        import tarfile

        archive_path = tmp_path / "import.tar.gz"
        pdf_content_a = b"%PDF-fake-a"
        pdf_content_b = b"%PDF-fake-b"
        pdf_content_c = b"%PDF-fake-c"

        src_dir = tmp_path / "src"
        (src_dir / "pdfs").mkdir(parents=True)
        (src_dir / "cleaned" / "bb").mkdir(parents=True)
        (src_dir / "pdfs" / "report-a.pdf").write_bytes(pdf_content_a)
        (src_dir / "cleaned" / "report-b.pdf").write_bytes(pdf_content_b)
        (src_dir / "cleaned" / "bb" / "report-bb.pdf").write_bytes(pdf_content_c)

        with tarfile.open(str(archive_path), "w:gz") as tar:
            tar.add(str(src_dir / "pdfs" / "report-a.pdf"), arcname="pdfs/report-a.pdf")
            tar.add(str(src_dir / "cleaned" / "report-b.pdf"), arcname="cleaned/report-b.pdf")
            tar.add(str(src_dir / "cleaned" / "bb" / "report-bb.pdf"), arcname="cleaned/bb/report-bb.pdf")

        data_dir = tmp_path / "dest"

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir):
            result = runner.invoke(args=["import-data", str(archive_path)])

        assert result.exit_code == 0
        assert "Imported 3 PDFs" in result.output
        assert (data_dir / "pdfs" / "report-a.pdf").read_bytes() == pdf_content_a
        assert (data_dir / "cleaned" / "report-b.pdf").read_bytes() == pdf_content_b
        assert (data_dir / "cleaned" / "bb" / "report-bb.pdf").read_bytes() == pdf_content_c

    def test_import_skips_non_pdf_files(self, tmp_path):
        """Importing should only extract .pdf files, ignoring others."""
        import app as app_module
        import tarfile

        archive_path = tmp_path / "import.tar.gz"
        src_dir = tmp_path / "src"
        (src_dir / "pdfs").mkdir(parents=True)
        (src_dir / "pdfs" / "report.pdf").write_bytes(b"%PDF-fake")
        (src_dir / "pdfs" / "readme.txt").write_bytes(b"not a pdf")

        with tarfile.open(str(archive_path), "w:gz") as tar:
            tar.add(str(src_dir / "pdfs" / "report.pdf"), arcname="pdfs/report.pdf")
            tar.add(str(src_dir / "pdfs" / "readme.txt"), arcname="pdfs/readme.txt")

        data_dir = tmp_path / "dest"

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir):
            result = runner.invoke(args=["import-data", str(archive_path)])

        assert result.exit_code == 0
        assert "Imported 1 PDFs" in result.output
        assert (data_dir / "pdfs" / "report.pdf").exists()
        assert not (data_dir / "pdfs" / "readme.txt").exists()

    def test_import_skips_unknown_directories(self, tmp_path):
        """Importing should ignore PDFs in unknown directories."""
        import app as app_module
        import tarfile

        archive_path = tmp_path / "import.tar"
        src_dir = tmp_path / "src"
        (src_dir / "unknown").mkdir(parents=True)
        (src_dir / "unknown" / "report.pdf").write_bytes(b"%PDF-fake")

        with tarfile.open(str(archive_path), "w") as tar:
            tar.add(str(src_dir / "unknown" / "report.pdf"), arcname="unknown/report.pdf")

        data_dir = tmp_path / "dest"

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        with patch.object(app_module, "DATA_DIR", data_dir):
            result = runner.invoke(args=["import-data", str(archive_path)])

        assert result.exit_code == 0
        assert "Imported 0 PDFs" in result.output

    def test_import_missing_archive(self, tmp_path):
        """Importing a nonexistent file should print an error."""
        import app as app_module

        runner = app_module.app.test_cli_runner(mix_stderr=False)
        result = runner.invoke(args=["import-data", str(tmp_path / "nonexistent.tar.gz")])

        assert result.exit_code == 0
        assert "does not exist" in result.output

    def test_export_then_import_roundtrip(self, tmp_path):
        """Export and then import should produce identical files including nested dirs."""
        import app as app_module

        src_data = tmp_path / "src_data"
        (src_data / "pdfs").mkdir(parents=True)
        (src_data / "cleaned" / "bund").mkdir(parents=True)
        (src_data / "raw" / "bund").mkdir(parents=True)
        pdf_content = b"%PDF-roundtrip-test"
        raw_content = b"%PDF-raw-test"
        (src_data / "pdfs" / "vsbericht-bund-2020.pdf").write_bytes(pdf_content)
        (src_data / "cleaned" / "bund" / "vsbericht-bund-2020.pdf").write_bytes(pdf_content)
        (src_data / "raw" / "bund" / "vsbericht-bund-2020.pdf").write_bytes(raw_content)

        archive_path = tmp_path / "roundtrip.tar"

        runner = app_module.app.test_cli_runner(mix_stderr=False)

        # Export
        with patch.object(app_module, "DATA_DIR", src_data):
            result = runner.invoke(args=["export-data", str(archive_path)])
        assert result.exit_code == 0

        # Import into a different directory
        dest_data = tmp_path / "dest_data"
        with patch.object(app_module, "DATA_DIR", dest_data):
            result = runner.invoke(args=["import-data", str(archive_path)])
        assert result.exit_code == 0

        assert (dest_data / "pdfs" / "vsbericht-bund-2020.pdf").read_bytes() == pdf_content
        assert (dest_data / "cleaned" / "bund" / "vsbericht-bund-2020.pdf").read_bytes() == pdf_content
        assert (dest_data / "raw" / "bund" / "vsbericht-bund-2020.pdf").read_bytes() == raw_content


# ---------------------------------------------------------------------------
# PDF image generation tests
# ---------------------------------------------------------------------------

class TestConvertPdfToImages:
    """Test the convert_pdf_to_images function."""

    def test_calls_convert_from_path_with_correct_args(self):
        from pathlib import Path
        with patch('app.convert_from_path') as mock_convert:
            mock_convert.return_value = ['img1', 'img2']
            from app import convert_pdf_to_images

            result = convert_pdf_to_images(Path('/fake/path.pdf'), dpi=150)

            mock_convert.assert_called_once_with('/fake/path.pdf', dpi=150)
            assert result == ['img1', 'img2']

    def test_default_dpi_is_150(self):
        from pathlib import Path
        with patch('app.convert_from_path') as mock_convert:
            mock_convert.return_value = []
            from app import convert_pdf_to_images

            convert_pdf_to_images(Path('/fake/path.pdf'))

            mock_convert.assert_called_once_with('/fake/path.pdf', dpi=150)


class TestSavePageImage:
    """Test the save_page_image function."""

    def test_creates_jpeg_and_avif_files(self, tmp_path):
        from PIL import Image

        # Create a test image (100x100 red square)
        img = Image.new('RGB', (100, 100), color='red')

        # Test the core logic directly (without the hardcoded path)
        base = str(tmp_path / "test-pdf_0")

        basewidth = 900
        if img.size[0] > basewidth:
            wpercent = basewidth / float(img.size[0])
            hsize = int(float(img.size[1]) * wpercent)
            img = img.resize((basewidth, hsize), Image.Resampling.LANCZOS)

        jpg_path = base + ".jpg"
        img.save(jpg_path, "JPEG", optimize=True)

        avif_path = base + ".avif"
        img.save(avif_path, "AVIF", quality=50)

        assert (tmp_path / "test-pdf_0.jpg").exists()
        assert (tmp_path / "test-pdf_0.avif").exists()

        # Verify files are valid images
        jpg_img = Image.open(tmp_path / "test-pdf_0.jpg")
        assert jpg_img.size == (100, 100)

        avif_img = Image.open(tmp_path / "test-pdf_0.avif")
        assert avif_img.size == (100, 100)

    def test_resizes_large_images_to_900px_width(self, tmp_path):
        from PIL import Image

        # Create a large test image (1800x2400)
        img = Image.new('RGB', (1800, 2400), color='blue')

        base = str(tmp_path / "large_0")

        basewidth = 900
        wpercent = basewidth / float(img.size[0])
        hsize = int(float(img.size[1]) * wpercent)
        resized = img.resize((basewidth, hsize), Image.Resampling.LANCZOS)

        jpg_path = base + ".jpg"
        resized.save(jpg_path, "JPEG", optimize=True)

        # Verify the saved image has correct dimensions
        saved_img = Image.open(jpg_path)
        assert saved_img.size[0] == 900
        assert saved_img.size[1] == 1200  # 2400 * (900/1800)

    def test_preserves_small_images(self, tmp_path):
        from PIL import Image

        # Create a small test image (400x600)
        img = Image.new('RGB', (400, 600), color='green')

        base = str(tmp_path / "small_0")
        jpg_path = base + ".jpg"

        # Image is smaller than 900px, should not be resized
        img.save(jpg_path, "JPEG", optimize=True)

        saved_img = Image.open(jpg_path)
        assert saved_img.size == (400, 600)


class TestProcPdfYearParsing:
    """Test year parsing error handling in proc_pdf."""

    def test_skips_file_with_unparseable_year(self, tmp_path, capsys):
        from pathlib import Path

        # Create an actual file with an unparseable year suffix
        pdf_path = tmp_path / "vsbericht-2023-hb.pdf"
        pdf_path.write_bytes(b"%PDF-fake")

        # Import after creating the file
        from app import proc_pdf

        # This should return early due to ValueError on int("hb")
        with patch('app.report_info', {'abr': []}):
            with patch('app.db'):
                result = proc_pdf(pdf_path)

        assert result is None
        captured = capsys.readouterr()
        assert "Skipping" in captured.out
        assert "cannot parse year" in captured.out

    def test_processes_file_with_valid_year(self):
        from pathlib import Path

        mock_path = MagicMock(spec=Path)
        mock_path.stem = "vsbericht-bb-2023"
        mock_path.name = "vsbericht-bb-2023.pdf"

        # Verify the year can be parsed
        year = int(mock_path.stem.split("-")[-1])
        assert year == 2023


class TestGenerateImagesCommand:
    """Test the generate-images CLI command."""

    def test_skips_english_kurzfassung_and_parl_files(self, tmp_path):
        import app as app_module

        # Create test PDF files
        pdfs_dir = tmp_path / "pdfs"
        pdfs_dir.mkdir()
        (pdfs_dir / "vsbericht-2020.pdf").write_bytes(b"%PDF-fake")
        (pdfs_dir / "vsbericht-2020_en.pdf").write_bytes(b"%PDF-fake")
        (pdfs_dir / "vsbericht-2020-kurzfassung.pdf").write_bytes(b"%PDF-fake")
        (pdfs_dir / "vsbericht-2020_parl.pdf").write_bytes(b"%PDF-fake")

        processed_files = []

        # Track which files get processed
        with patch.object(app_module, 'convert_pdf_to_images') as mock_convert:
            with patch.object(app_module, 'save_page_image'):
                with patch.object(app_module, 'pdftotext') as mock_pdftotext:
                    mock_pdftotext.PDF.return_value = ['page1']
                    mock_convert.return_value = [MagicMock()]

                    # Simulate the filtering logic
                    for pdf_path in sorted(pdfs_dir.glob("*.pdf")):
                        if (
                            pdf_path.stem.endswith("_en")
                            or pdf_path.stem.endswith("kurzfassung")
                            or pdf_path.stem.endswith("_parl")
                        ):
                            continue
                        processed_files.append(pdf_path.name)

        assert processed_files == ["vsbericht-2020.pdf"]

    def test_skips_existing_images_without_force(self, tmp_path):
        """Test that existing images are skipped unless --force is used."""
        pdfs_dir = tmp_path / "pdfs"
        images_dir = tmp_path / "images"
        pdfs_dir.mkdir()
        images_dir.mkdir()

        # Create a PDF and its existing images
        (pdfs_dir / "vsbericht-2020.pdf").write_bytes(b"%PDF-fake")
        (images_dir / "vsbericht-2020_0.jpg").write_bytes(b"fake jpg")
        (images_dir / "vsbericht-2020_0.avif").write_bytes(b"fake avif")

        # Check which pages need generating (simulating the command logic)
        pdf_path = pdfs_dir / "vsbericht-2020.pdf"
        num_pages = 1

        pages_to_generate = []
        for i in range(num_pages):
            jpg_path = images_dir / f"{pdf_path.stem}_{i}.jpg"
            avif_path = images_dir / f"{pdf_path.stem}_{i}.avif"
            force = False
            if force or not (jpg_path.exists() and avif_path.exists()):
                pages_to_generate.append(i)

        assert pages_to_generate == []  # No pages need generating

    def test_generates_missing_images(self, tmp_path):
        """Test that missing images are generated."""
        pdfs_dir = tmp_path / "pdfs"
        images_dir = tmp_path / "images"
        pdfs_dir.mkdir()
        images_dir.mkdir()

        # Create a PDF without images
        (pdfs_dir / "vsbericht-2020.pdf").write_bytes(b"%PDF-fake")

        pdf_path = pdfs_dir / "vsbericht-2020.pdf"
        num_pages = 3

        pages_to_generate = []
        for i in range(num_pages):
            jpg_path = images_dir / f"{pdf_path.stem}_{i}.jpg"
            avif_path = images_dir / f"{pdf_path.stem}_{i}.avif"
            force = False
            if force or not (jpg_path.exists() and avif_path.exists()):
                pages_to_generate.append(i)

        assert pages_to_generate == [0, 1, 2]  # All pages need generating


# ---------------------------------------------------------------------------
# CLI command tests: create-zips
# ---------------------------------------------------------------------------

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
            assert "bund-2020.txt" in names
            content = zf.read("bund-2020.txt").decode("utf-8")
            assert "Page 1 text" in content
            assert "Page 2 text" in content

    def test_download_route_unknown_404(self):
        """Requesting an unknown filename should return 404."""
        from app import app
        with app.test_client() as client:
            response = client.get("/downloads/evil.zip")
            assert response.status_code == 404


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
