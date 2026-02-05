"""CLI command tests: export-data / import-data."""

from unittest.mock import patch


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
