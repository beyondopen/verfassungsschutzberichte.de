# AVIF Image Support Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Serve PDF page scans in AVIF format at 2x resolution (1800px) with JPEG fallback (900px).

**Architecture:** Extract PDF pages at higher DPI, generate both JPEG (900px) and AVIF (1800px) variants. Serve via `<picture>` elements with lazysizes. New `flask generate-images` CLI command for bulk (re)generation.

**Tech Stack:** Flask, Pillow 10.3 (native AVIF), pdf2image, lazysizes, Jinja2

---

### Task 1: Add libavif to Dockerfile

**Files:**
- Modify: `Dockerfile:3`

**Step 1: Add libavif-dev to apt-get install**

In `Dockerfile`, line 3, add `libavif-dev` to the package list:

```dockerfile
RUN apt-get update -y && apt-get upgrade -y && apt-get install -y build-essential libpoppler-cpp-dev pkg-config python-dev-is-python3 poppler-utils libavif-dev
```

**Step 2: Commit**

```bash
git add Dockerfile
git commit -m "feat: add libavif-dev to Dockerfile for AVIF support"
```

---

### Task 2: Extract image generation into reusable function

**Files:**
- Modify: `src/app.py:183-195`

**Step 1: Create `generate_page_images` function**

Add a new function above `proc_pdf` (around line 133, after `special_pdf_preproc`) that handles image generation for a single PDF page:

```python
def generate_page_images(pdf_path, page_index, dpi=300):
    """Generate JPEG (900px) and AVIF (1800px) for a single PDF page.

    Args:
        pdf_path: Path to the PDF file
        page_index: 0-based page index
        dpi: DPI for PDF rendering (300 gives enough resolution for 1800px)
    """
    images = convert_from_path(str(pdf_path), first_page=page_index + 1, last_page=page_index + 1, dpi=dpi)
    img = images[0]
    stem = pdf_path.stem
    base = "/data/images/" + stem + "_" + str(page_index)

    # JPEG at 900px
    jpg_path = base + ".jpg"
    jpg_img = img
    basewidth = 900
    if img.size[0] > basewidth:
        wpercent = basewidth / float(img.size[0])
        hsize = int(float(img.size[1]) * wpercent)
        jpg_img = img.resize((basewidth, hsize), Image.Resampling.LANCZOS)
    jpg_img.save(jpg_path, "JPEG", optimize=True)

    # AVIF at 1800px
    avif_path = base + ".avif"
    avif_width = 1800
    if img.size[0] > avif_width:
        wpercent = avif_width / float(img.size[0])
        hsize = int(float(img.size[1]) * wpercent)
        avif_img = img.resize((avif_width, hsize), Image.Resampling.LANCZOS)
    elif img.size[0] > 900:
        avif_img = img
    else:
        # Source too small for a meaningful AVIF upgrade, skip
        return jpg_path
    avif_img.save(avif_path, "AVIF", quality=63)

    return jpg_path
```

**Step 2: Update `proc_pdf` to use the new function**

Replace lines 184-195 in `proc_pdf`:

```python
            # Old:
            images = convert_from_path(str(pdf_path), first_page=i + 1, last_page=i + 1)
            fname = "/data" + "/images/" + pdf_path.stem + "_" + str(i) + ".jpg"
            img = images[0]
            basewidth = 900
            if img.size[0] > basewidth:
                wpercent = basewidth / float(img.size[0])
                hsize = int((float(img.size[1]) * float(wpercent)))
                img = img.resize((basewidth, hsize), Image.Resampling.LANCZOS)
            img.save(fname, optimize=True)
```

With:

```python
            fname = generate_page_images(pdf_path, i)
```

**Step 3: Commit**

```bash
git add src/app.py
git commit -m "feat: extract image generation into reusable function with AVIF support"
```

---

### Task 3: Add `flask generate-images` CLI command

**Files:**
- Modify: `src/app.py` (add after `clear_data` command, around line 265)

**Step 1: Add the CLI command**

```python
@app.cli.command()
@click.argument("pattern")
@click.option("--force", is_flag=True, help="Regenerate existing images")
def generate_images(pattern="*", force=False):
    """Generate JPEG and AVIF images from PDFs. Usage: flask generate-images '*'"""
    for pdf_path in sorted(Path("/data/pdfs").glob(pattern + ".pdf")):
        if (
            pdf_path.stem.endswith("_en")
            or pdf_path.stem.endswith("kurzfassung")
            or pdf_path.stem.endswith("_parl")
        ):
            continue

        print(f"Processing {pdf_path.name}")
        with open(pdf_path, "rb") as f:
            pdf = pdftotext.PDF(f)
            num_pages = len(pdf)

        for i in range(num_pages):
            jpg_path = "/data/images/" + pdf_path.stem + "_" + str(i) + ".jpg"
            avif_path = "/data/images/" + pdf_path.stem + "_" + str(i) + ".avif"

            if not force and Path(jpg_path).exists() and Path(avif_path).exists():
                continue

            print(f"  Page {i + 1}/{num_pages}")
            generate_page_images(pdf_path, i)
```

**Step 2: Commit**

```bash
git add src/app.py
git commit -m "feat: add flask generate-images CLI command"
```

---

### Task 4: Update image serving route for AVIF content type

**Files:**
- Modify: `src/app.py:630-643`

**Step 1: Update `download_img` to detect file extension**

Replace the current `download_img` function:

```python
@app.route("/images/<path:filename>")
def download_img(filename):
    if app.debug:
        return send_from_directory("/data/images", filename)

    content_type = "image/avif" if filename.endswith(".avif") else "image/jpeg"
    resp = make_response(send_from_directory("/data/images", filename))
    resp.headers["Content-Type"] = content_type
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp
```

**Step 2: Commit**

```bash
git add src/app.py
git commit -m "feat: serve AVIF images with correct content type"
```

---

### Task 5: Update `details.html` template with `<picture>` elements

**Files:**
- Modify: `src/templates/details.html:172-179`

**Step 1: Replace `<img>` with `<picture>`**

Replace:

```html
<div>
  <img
    style="width: 100%"
    data-src="{{p.file_url}}"
    class="lazyload"
    alt="Seite {{p.page_number}}"
  />
</div>
```

With:

```html
<div>
  <picture>
    <source
      type="image/avif"
      data-srcset="{{p.file_url|replace('.jpg', '.avif')}}"
    />
    <img
      style="width: 100%"
      data-src="{{p.file_url}}"
      class="lazyload"
      alt="Seite {{p.page_number}}"
    />
  </picture>
</div>
```

**Step 2: Commit**

```bash
git add src/templates/details.html
git commit -m "feat: use picture element with AVIF source in details template"
```

---

### Task 6: Update `search.html` template with `<picture>` elements

**Files:**
- Modify: `src/templates/search.html:290-297`

**Step 1: Replace `<img>` with `<picture>`**

Replace:

```html
    <div>
      <img
        style="width: 100%"
        data-src="{{r.file_url}}"
        class="lazyload"
        alt="{{r.content}}"
      />
    </div>
```

With:

```html
    <div>
      <picture>
        <source
          type="image/avif"
          data-srcset="{{r.file_url|replace('.jpg', '.avif')}}"
        />
        <img
          style="width: 100%"
          data-src="{{r.file_url}}"
          class="lazyload"
          alt="{{r.content}}"
        />
      </picture>
    </div>
```

**Step 2: Commit**

```bash
git add src/templates/search.html
git commit -m "feat: use picture element with AVIF source in search template"
```
