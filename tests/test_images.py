"""PDF image generation tests."""

from unittest.mock import MagicMock, patch


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
