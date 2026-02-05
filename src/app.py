import json
import os
import re
import shutil
import tarfile
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, unquote

import cleantext
import click
import frontmatter
import markdown
import pdftotext
import spacy
from flask import (
    Flask,
    abort,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
)
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_sqlalchemy.query import Query
from pdf2image import convert_from_path
from PIL import Image
from sqlalchemy import func
from sqlalchemy.sql import text
from sqlalchemy_searchable import SearchQueryMixin, make_searchable, sql_expressions
from sqlalchemy_utils.types import TSVectorType

from report_info import report_info

app = Flask(__name__)

if app.debug:
    url = "postgresql+psycopg2://postgres:password@db:5432/postgres"
    time.sleep(10)
    app.config["CACHE_TYPE"] = "null"
else:
    url = os.environ["DATABASE_URL"]
    # Fix for SQLAlchemy 1.4+: replace postgres:// with postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    app.config["CACHE_TYPE"] = "redis"
    app.config["CACHE_REDIS_URL"] = os.environ["REDIS_URL"]
    app.config["CACHE_DEFAULT_TIMEOUT"] = 60 * 60  # 1 hour

app.config["SQLALCHEMY_DATABASE_URI"] = url

# remove whitespaces from HTML
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True


cache = Cache(app)

db = SQLAlchemy(app)

make_searchable(db.metadata, options={"regconfig": "pg_catalog.german"})


class DocumentQuery(Query, SearchQueryMixin):
    pass


class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer)
    title = db.Column(db.String)
    jurisdiction = db.Column(db.String)
    file_url = db.Column(db.String, unique=True)
    num_pages = db.Column(db.Integer)


class DocumentPage(db.Model):
    query_class = DocumentQuery

    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    document = db.relationship(
        "Document",
        backref=db.backref("pages", lazy=True, order_by="DocumentPage.page_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    page_number = db.Column(db.Integer)
    content = db.Column(db.UnicodeText)
    file_url = db.Column(db.String, unique=True)
    search_vector = db.Column(TSVectorType("content"))


class TokenCount(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    document_id = db.Column(db.Integer, db.ForeignKey("document.id"), nullable=False)
    document = db.relationship("Document", backref=db.backref("counts"), lazy=True)

    token = db.Column(db.String)
    count = db.Column(db.Integer)


db.configure_mappers()  # very important!

# Create parse_websearch function for SQLAlchemy-Searchable 2.0+
with app.app_context():
    try:
        db.session.execute(text(sql_expressions.statement))
        db.session.commit()
    except Exception:
        # Function may already exist
        db.session.rollback()

    if app.debug:
        db.create_all()
        db.session.commit()


DATA_DIR = Path("/data")
PDF_DIR = DATA_DIR / "pdfs"
ZIP_DIR = DATA_DIR / "zips"

jurisdictions = ["Bund"] + [
    l[1] for l in sorted(report_info["abr"], key=lambda x: x[1])
]

nlp = spacy.blank("de")


def count_tokens(texts):
    c = Counter()
    for d in nlp.tokenizer.pipe(texts):
        c.update([str(t).lower() for t in d])
    return c


# TODO: often there are news lines instead of hyphens betwen the words
regex_join_words = re.compile(r"(?<=\S\S)-\s+(?=\S{2,})")


def special_pdf_preproc(s):
    s = regex_join_words.sub("", s)
    return s


def convert_pdf_to_images(pdf_path, dpi=150):
    """Convert entire PDF to images at once (much faster than per-page)."""
    return convert_from_path(str(pdf_path), dpi=dpi)


def save_page_image(img, pdf_stem, page_index):
    """Save a single page image as JPEG and AVIF at 900px width."""
    base = "/data/images/" + pdf_stem + "_" + str(page_index)

    basewidth = 900
    if img.size[0] > basewidth:
        wpercent = basewidth / float(img.size[0])
        hsize = int(float(img.size[1]) * wpercent)
        img = img.resize((basewidth, hsize), Image.Resampling.LANCZOS)

    # JPEG at 900px
    jpg_path = base + ".jpg"
    img.save(jpg_path, "JPEG", optimize=True)

    # AVIF at 900px
    avif_path = base + ".avif"
    img.save(avif_path, "AVIF", quality=50)

    return jpg_path


def proc_pdf(pdf_path):
    # no engl for now, no kurzfassung
    if (
        pdf_path.stem.endswith("_en")
        or pdf_path.stem.endswith("kurzfassung")
        or pdf_path.stem.endswith("_parl")
    ):
        return

    juris = "Bund"
    for [a, b] in report_info["abr"]:
        if a.lower() == str(pdf_path.name.split("-")[1]):
            juris = b
    try:
        year = int(pdf_path.stem.split("-")[-1])
    except ValueError:
        print(f"Skipping {pdf_path.name}: cannot parse year from filename")
        return

    doc = Document(
        year=year,
        jurisdiction=juris,
        title=f"Verfassungsschutzbericht {year}",
        file_url="/pdfs/" + pdf_path.name,
    )

    print(pdf_path)

    db.session.add(doc)
    db.session.commit()

    # Convert all PDF pages to images at once (much faster than per-page)
    page_images = convert_pdf_to_images(pdf_path)

    with open(pdf_path, "rb") as f:
        pdf = pdftotext.PDF(f)
        texts = []

        # Extract text from all pages (fast, sequential)
        for page_text in pdf:
            page_text = cleantext.clean(
                page_text, lang="de", lower=False, no_line_breaks=True
            )
            page_text = special_pdf_preproc(page_text)
            texts.append(page_text)

        num_pages = len(texts)

        # Save images in parallel - ThreadPoolExecutor achieves true parallelism here
        # because Pillow's AVIF encoder releases the GIL during encoding operations
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(save_page_image, page_images[i], pdf_path.stem, i)
                for i in range(num_pages)
            ]
            image_paths = [f.result() for f in futures]

        # Create DocumentPage objects with results
        for i, (page_text, fname) in enumerate(zip(texts, image_paths)):
            print(i)
            p = DocumentPage(
                document=doc,
                content=page_text,
                page_number=i + 1,
                file_url=fname.replace("/data", ""),
            )
            db.session.add(p)

        counts = count_tokens(texts)
        for token in counts:
            tc = TokenCount(document=doc, token=token, count=counts[token])
            db.session.add(tc)

    doc.num_pages = num_pages
    db.session.commit()


@app.cli.command()
def init_db():
    db.create_all()
    db.session.commit()


@app.cli.command()
def clear_cache():
    cache.clear()


@app.cli.command()
@click.argument("pattern")
def update_docs(pattern="*"):
    Path("/data/images").mkdir(parents=True, exist_ok=True)
    # only add documents that are not already entered
    for pdf_path in Path("/data" + "/pdfs").glob(pattern + ".pdf"):
        try:
            proc_pdf(pdf_path)
        except Exception as e:
            print(pdf_path, " error, already added?")
            print(e)
            db.session.rollback()
    cache.clear()


@app.cli.command()
@click.argument("pattern")
def remove_docs(pattern="*"):
    try:
        # fucked up cascade on creation of db schema, so a a work-around
        doc = Document.query.filter(Document.file_url == "/pdfs/" + pattern).first()
        TokenCount.query.filter(TokenCount.document_id == doc.id).delete()
        DocumentPage.query.filter(DocumentPage.document_id == doc.id).delete()
        Document.query.filter(Document.file_url == "/pdfs/" + pattern).delete()
        db.session.commit()
    except Exception as e:
        print(e)
        db.session.rollback()
    cache.clear()


@app.cli.command()
def clear_data():
    # delete all data and caches, add new documents
    db.drop_all()
    db.session.commit()

    cache.clear()

    db.configure_mappers()  # very important!
    db.create_all()
    db.session.commit()

    Path("/data/images").mkdir(parents=True, exist_ok=True)
    for pdf_path in Path("/data/pdfs").glob("*.pdf"):
        proc_pdf(pdf_path)


@app.cli.command()
@click.argument("pattern")
@click.option("--force", is_flag=True, help="Regenerate existing images")
def generate_images(pattern="*", force=False):
    """Generate JPEG and AVIF images from PDFs. Usage: flask generate-images '*'"""
    Path("/data/images").mkdir(parents=True, exist_ok=True)
    for pdf_path in sorted(Path("/data/pdfs").glob(pattern + ".pdf")):
        if (
            pdf_path.stem.endswith("_en")
            or pdf_path.stem.endswith("kurzfassung")
            or pdf_path.stem.endswith("_parl")
        ):
            continue

        # Check which pages need generating
        with open(pdf_path, "rb") as f:
            pdf = pdftotext.PDF(f)
            num_pages = len(pdf)

        pages_to_generate = []
        for i in range(num_pages):
            jpg_path = "/data/images/" + pdf_path.stem + "_" + str(i) + ".jpg"
            avif_path = "/data/images/" + pdf_path.stem + "_" + str(i) + ".avif"
            if force or not (Path(jpg_path).exists() and Path(avif_path).exists()):
                pages_to_generate.append(i)

        if not pages_to_generate:
            continue

        print(f"Processing {pdf_path.name} ({len(pages_to_generate)} pages)")
        page_images = convert_pdf_to_images(pdf_path)

        # Save images in parallel - ThreadPoolExecutor achieves true parallelism
        # because Pillow's AVIF encoder releases the GIL during encoding
        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(save_page_image, page_images[i], pdf_path.stem, i)
                for i in pages_to_generate
            ]
            for f in futures:
                f.result()  # Wait for completion and raise any exceptions


DATA_DIRS = ["pdfs", "cleaned", "raw", "deleted"]


@app.cli.command()
@click.argument("output_path")
def export_data(output_path):
    """Export all data directories as a tar archive."""
    total = 0
    with tarfile.open(output_path, "w") as tar:
        for dir_name in DATA_DIRS:
            dir_path = DATA_DIR / dir_name
            if not dir_path.exists():
                continue
            for f in sorted(dir_path.rglob("*.pdf")):
                rel = f.relative_to(DATA_DIR)
                tar.add(str(f), arcname=str(rel))
                print(f"  Added {rel}")
                total += 1

    if total == 0:
        print("No PDF files found")
    else:
        print(f"Exported {total} PDFs to {output_path}")


@app.cli.command()
@click.argument("input_path")
def import_data(input_path):
    """Import PDFs from a tar archive into /data/ directories."""
    input_file = Path(input_path)
    if not input_file.exists():
        print(f"Error: {input_path} does not exist")
        return

    with tarfile.open(input_path, "r:*") as tar:
        members = [m for m in tar.getmembers() if m.name.endswith(".pdf")]
        total = 0
        for member in members:
            parts = Path(member.name).parts
            if len(parts) >= 2 and parts[0] in DATA_DIRS:
                dest = DATA_DIR / Path(member.name).parent
                dest.mkdir(parents=True, exist_ok=True)
                tar.extract(member, path=str(DATA_DIR))
                print(f"  Extracted {member.name}")
                total += 1

    print(f"Imported {total} PDFs")


def _build_pdf_zip(force):
    """Build ZIP archive of all PDFs."""
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    dest = ZIP_DIR / "vsberichte.zip"
    tmp = ZIP_DIR / "vsberichte.zip.tmp"

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    disk_files = {p.name: p.stat().st_size for p in pdfs}

    existing = {}
    needs_rebuild = force or not dest.exists()

    if not needs_rebuild:
        with zipfile.ZipFile(str(dest), "r") as zf:
            existing = {i.filename: i.file_size for i in zf.infolist()}
        # Check if any zip entry was deleted or changed on disk
        for name, size in existing.items():
            if disk_files.get(name) != size:
                needs_rebuild = True
                break

    if needs_rebuild:
        # Full rebuild
        if tmp.exists():
            tmp.unlink()
        with zipfile.ZipFile(str(tmp), "w", compression=zipfile.ZIP_STORED) as zf:
            for pdf in pdfs:
                zf.write(str(pdf), pdf.name)
        shutil.move(str(tmp), str(dest))
        print(f"PDF ZIP: {len(pdfs)} files (rebuilt)")
    else:
        new_files = [p for p in pdfs if p.name not in existing]
        if not new_files:
            print(f"PDF ZIP: {len(existing)} files (up to date)")
            return
        # Append only new files
        with zipfile.ZipFile(str(dest), "a") as zf:
            for pdf in new_files:
                zf.write(str(pdf), pdf.name)
        print(f"PDF ZIP: {len(existing) + len(new_files)} files ({len(new_files)} new)")


def _build_text_zip():
    """Build ZIP archive of text exports from the database."""
    ZIP_DIR.mkdir(parents=True, exist_ok=True)
    dest = ZIP_DIR / "vsberichte-texts.zip"
    tmp = ZIP_DIR / "vsberichte-texts.zip.tmp"

    if tmp.exists():
        tmp.unlink()

    docs = Document.query.order_by(Document.jurisdiction, Document.year).all()
    total = 0
    with zipfile.ZipFile(str(tmp), "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for doc in docs:
            text = "\n\n\n".join([p.content for p in doc.pages])
            fname = Path(doc.file_url).stem + ".txt"
            zf.writestr(fname, text)
            total += 1

    shutil.move(str(tmp), str(dest))
    print(f"Text ZIP: {total} files")


@app.cli.command("create-zips")
@click.option("--force", is_flag=True, help="Rebuild from scratch")
@click.option("--pdfs/--no-pdfs", default=True)
@click.option("--texts/--no-texts", default=True)
def create_zips(force, pdfs, texts):
    """Create ZIP archives of all PDFs and text exports."""
    if pdfs:
        print("Building PDF ZIP...")
        _build_pdf_zip(force)
    if texts:
        print("Building text ZIP...")
        _build_text_zip()
    print("Done.")


def get_index():
    res = []
    total = 0
    for x in jurisdictions:
        years = []
        for d in (
            Document.query.filter_by(jurisdiction=x)
            .order_by(Document.year.desc())
            .all()
        ):
            years.append(d.year)
            total += 1
        res.append({"jurisdiction": x, "years": years})
    return res, total


# Blog functions
def get_blog_posts():
    """Load all blog posts from markdown files."""
    # In Docker, src/ is mounted at /app/, so blog posts are at /app/blog/posts/
    blog_dir = Path("/app/blog/posts")
    if not blog_dir.exists():
        return []

    posts = []
    for md_file in blog_dir.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                # Render markdown and wrap tables for responsiveness
                html_content = markdown.markdown(
                    post.content,
                    extensions=["fenced_code", "codehilite", "tables"]
                )
                # Wrap tables in a responsive container
                html_content = html_content.replace(
                    '<table>',
                    '<div class="table-responsive"><table>'
                ).replace('</table>', '</table></div>')

                post_data = {
                    "title": post.get("title", ""),
                    "date": post.get("date"),
                    "tags": post.get("tags", []),
                    "slug": post.get("slug", md_file.stem),
                    "content": html_content,
                }
                posts.append(post_data)
        except Exception as e:
            print(f"Error loading {md_file}: {e}")

    # Sort by date, newest first
    posts.sort(key=lambda x: x["date"], reverse=True)
    return posts


def get_blog_post(slug):
    """Load a single blog post by slug."""
    # In Docker, src/ is mounted at /app/, so blog posts are at /app/blog/posts/
    blog_dir = Path("/app/blog/posts")

    # Find the markdown file with this slug
    for md_file in blog_dir.glob("*.md"):
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                post = frontmatter.load(f)
                if post.get("slug") == slug or md_file.stem.endswith(slug):
                    # Render markdown and wrap tables for responsiveness
                    html_content = markdown.markdown(
                        post.content,
                        extensions=["fenced_code", "codehilite", "tables"]
                    )
                    # Wrap tables in a responsive container
                    html_content = html_content.replace(
                        '<table>',
                        '<div class="table-responsive"><table>'
                    ).replace('</table>', '</table></div>')

                    return {
                        "title": post.get("title", ""),
                        "date": post.get("date"),
                        "tags": post.get("tags", []),
                        "slug": post.get("slug", md_file.stem),
                        "content": html_content,
                    }
        except Exception as e:
            print(f"Error loading {md_file}: {e}")

    return None


@app.route("/")
@cache.cached(timeout=60 * 60)
def index():
    res, total = get_index()
    return render_template("index.html", docs=res, total=total)


@app.route("/berichte")
@cache.cached(timeout=60 * 60)
def reports():
    res, total = get_index()
    return render_template(
        "reports.html", docs=res, total=total, report_info=report_info
    )


@app.route("/<jurisdiction>/<int:year>")
@cache.cached()
def details(jurisdiction, year):
    jurisdiction = jurisdiction.title()
    d = Document.query.filter_by(jurisdiction=jurisdiction, year=year).first()

    if d is None:
        abort(404)

    sumed = (
        TokenCount.query.filter(TokenCount.document_id == d.id)
        .with_entities(func.sum(TokenCount.count))
        .scalar()
    )
    return render_template("details.html", d=d, counts=sumed, report_info=report_info)


def build_query():
    q = request.args.get("q")
    page = int(request.args.get("page", 1))
    jurisdiction = request.args.get("jurisdiction")
    min_year = request.args.get("min_year", "kein")
    max_year = request.args.get("max_year", "kein")

    if not jurisdiction is None:
        jurisdiction = unquote(jurisdiction)

    if jurisdiction == "alle":
        jurisdiction = None

    if min_year == "kein":
        min_year = None
    else:
        min_year = int(min_year)

    if max_year == "kein":
        max_year = None
    else:
        max_year = int(max_year)

    if q is None:
        return None

    query = DocumentPage.query

    if jurisdiction is not None or min_year is not None or max_year is not None:
        query = query.join(Document)

    if jurisdiction is not None:
        query = query.filter(Document.jurisdiction == jurisdiction.title())

    if min_year is not None:
        query = query.filter(Document.year >= min_year)

    if max_year is not None:
        query = query.filter(Document.year <= max_year)
    return query, page, jurisdiction, max_year, min_year


# need more documents to get analysis on earlier years
trends_min_year = 1993


@cache.cached(key_prefix="total_years")
def get_year_totals():
    year_total = (
        TokenCount.query.join(Document)
        .filter(Document.year >= trends_min_year)
        .group_by(Document.year)
        .values(Document.year, func.sum(TokenCount.count))
    )
    return list(year_total)


@app.route("/stats")
@cache.cached(query_string=True)
def stats():
    q = request.args.get("q")
    if q is None:
        return jsonify({})
    q = cleantext.clean(q, lang="de")
    # for qs like "token" remove the quotes to count
    counting_q = q.replace('"', "").replace("'", "")

    query, page, jurisdiction, max_year, min_year = build_query()

    all_results = (
        query.join(Document)
        .filter(Document.year >= trends_min_year)
        .search(q)
        .with_entities(Document.year, DocumentPage.content)
    )
    d = defaultdict(int)

    for r in all_results:
        year = r.year
        count = r.content.lower().count(counting_q)
        d[year] += count

    for year_tup in get_year_totals():
        d[year_tup[0]] /= year_tup[1]

    # fix NSU
    if q.lower() == "nsu":
        for y in range(trends_min_year, 2009):
            d[y] = 0

    return jsonify([q, d])


@app.route("/trends")
@cache.cached(query_string=True)
def trends():
    qs = request.args.getlist("q")
    if len(qs) == 0 and not app.debug:
        return redirect("/trends?q=nsu&q=raf")
    return render_template("trends.html", qs=qs)


@app.route("/regional")
@cache.cached(query_string=True)
def regional():
    q = request.args.get("q")
    if q is None and not app.debug:
        return redirect("/regional?q=vvn-bda")
    return render_template("regional.html", q=q)


@app.route("/impressum")
@cache.cached()
def impressum():
    return render_template("impressum.html")


# Blog routes
@app.route("/blog/")
@cache.cached(timeout=60 * 30)  # 30 minutes cache for blog index
def blog_index():
    posts = get_blog_posts()
    return render_template("blog_index.html", posts=posts)


@app.route("/blog/<slug>")
@cache.cached(timeout=60 * 30)  # 30 minutes cache for blog posts
def blog_post(slug):
    post = get_blog_post(slug)
    if post is None:
        abort(404)
    return render_template("blog_post.html", post=post)


@app.route("/blog/images/<path:filename>")
def blog_image(filename):
    # In Docker, src/ is mounted at /app/, so blog images are at /app/blog/images/
    blog_img_dir = "/app/blog/images"
    return send_from_directory(blog_img_dir, filename)


@app.route("/suche")
@cache.cached(query_string=True)
def search():
    q = request.args.get("q")
    if q is None or len(q) == 0:
        return render_template("search.html", q=None)
    q = cleantext.clean(q, lang="de")
    query, page, jurisdiction, max_year, min_year = build_query()

    results = query.search(q, sort=True).paginate(page=page, per_page=20, error_out=True).items

    # get counts for the years, only select ID for performance
    count_sq = query.search(q).with_entities(DocumentPage.id)
    num_results = count_sq.count()
    counts = (
        DocumentPage.query.with_entities(DocumentPage.id)
        .filter(DocumentPage.id.in_(count_sq.subquery()))
        .join(Document)
        .group_by(Document.year)
        .values(Document.year, func.count(DocumentPage.id))
    )
    c_d = {}
    for c in counts:
        c_d[c[0]] = c[1]
    counts = json.dumps(c_d)

    tokens = (
        q.replace('"', "").replace("'", "").replace("(", "").replace(")", "").split()
    )
    # filter out negations
    tokens = [t for t in tokens if t[0] != "-" and t.lower() not in ("or", "and")]

    # generate the snippets to display search results, use text against sql injection
    ids = ", ".join([str(x.id) for x in results])
    ids_int = [x.id for x in results]
    if len(ids_int) > 0:
        snips = db.session.execute(
            text(
                f"SELECT id, ts_headline(content, parse_websearch('pg_catalog.german', '{q}'), 'MaxFragments=10, MinWords=5, MaxWords=20, FragmentDelimiter=XXX.....XXX') as text FROM {DocumentPage.__tablename__} WHERE id in ({ids})"
            )
        )
    else:
        snips = []

    for s in snips:
        results[ids_int.index(s.id)].snips = s.text.split("XXX.....XXX")

    response = make_response(
        render_template(
            "search.html",
            results=results,
            jurisdiction=jurisdiction,
            min_year=min_year,
            max_year=max_year,
            q=q,
            n=num_results,
            page=page,
            min_page=max(1, page - 5),
            max_page=min((num_results - 1) // 20 + 1, page + 5),
            counts=counts,
            report_info=report_info,
        )
    )
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@app.route("/robots.txt")
@cache.cached()
def static_from_root():
    return send_from_directory("static", request.path[1:])


# FILES
# ensure the files are served by nginx


@app.route("/pdfs/<path:filename>")
def download_pdf(filename):
    if app.debug:
        return send_from_directory("/data/pdfs", filename)
    resp = make_response()
    resp.headers["X-Accel-Redirect"] = f"/internal-pdfs/{filename}"
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.route("/images/<path:filename>")
def download_img(filename):
    if app.debug:
        return send_from_directory("/data/images", filename)
    content_type = "image/avif" if filename.endswith(".avif") else "image/jpeg"
    resp = make_response()
    resp.headers["X-Accel-Redirect"] = f"/internal-images/{filename}"
    resp.headers["Content-Type"] = content_type
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@app.route("/downloads/<path:filename>")
def download_file(filename):
    allowed = {"vsberichte.zip", "vsberichte-texts.zip"}
    if filename not in allowed:
        abort(404)
    if app.debug:
        return send_from_directory(str(ZIP_DIR), filename)
    resp = make_response()
    resp.headers["X-Accel-Redirect"] = f"/internal-zips/{filename}"
    resp.headers["Content-Type"] = "application/zip"
    resp.headers["Content-Disposition"] = f"attachment; filename={filename}"
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


# API


def serialize_doc(d):
    return {
        "year": d.year,
        "title": d.title,
        "jurisdiction": d.jurisdiction,
        "file_url": "https://verfassungsschutzberichte.de" + d.file_url,
        "num_pages": d.num_pages,
    }


@app.route("/api/<jurisdiction>/<int:year>")
@cache.cached()
def api_details(jurisdiction, year):
    jurisdiction = jurisdiction.title()
    d = Document.query.filter_by(jurisdiction=jurisdiction, year=year).first()
    if d is None:
        abort(404)
    res = serialize_doc(d)
    res["pages"] = [x.content for x in d.pages]
    return jsonify(res)


@app.route("/api")
@cache.cached()
def api_index():
    res, total = get_index()
    for x in res:
        x["jurisdiction_escaped"] = quote(x["jurisdiction"].lower())
    return jsonify({"reports": res, "total": total})


@app.route("/api/auto-complete")
@cache.cached(query_string=True)
def api_search_auto():
    # TODO: respect min/max year etc.

    q_orig = request.args.get("q", "").lower()
    if q_orig == "":
        return jsonify([])

    if (
        '"' in q_orig
        or " and " in q_orig
        or " or " in q_orig
        or "(" in q_orig
        or ")" in q_orig
    ):
        return jsonify([])
    q_list = q_orig.split()
    q = q_list[-1]

    if len(q_list) == 1:
        results = (
            TokenCount.query.filter(TokenCount.token.like(q + "%"))
            .order_by(TokenCount.count.desc())
            .limit(100)
        )
    else:
        # make sure previous tokens appear on the same document page
        ids = None
        for t in q_list[:-1]:
            res = set(
                r[0] for r in TokenCount.query.filter(TokenCount.token == t)
                .with_entities(TokenCount.document_id)
                .all()
            )
            if ids is None:
                ids = res
            else:
                ids = ids.intersection(res)
        if not ids:
            return jsonify([])
        results = (
            TokenCount.query.filter(TokenCount.token.like(q + "%"))
            .filter(TokenCount.document_id.in_(ids))
            .order_by(TokenCount.count.desc())
            .limit(100)
        )

    res = []
    for x in results:
        if not x.token in res:
            res.append(x.token)
    return jsonify([" ".join(q_list[:-1] + [x]) for x in res[:10]])


@app.route("/api/mentions")
@cache.cached(query_string=True)
def api_mentions():
    q = request.args.get("q")

    to_csv = not request.args.get("csv") is None

    if q is None or len(q) == 0:
        abort(404)
    q = cleantext.clean(q, lang="de")
    query, page, jurisdiction, max_year, min_year = build_query()

    # Set default min/max years if not provided
    if min_year is None:
        min_year = db.session.query(func.min(Document.year)).scalar()
    if max_year is None:
        max_year = db.session.query(func.max(Document.year)).scalar()

    # get counts for the years, only select ID for performance
    count_sq = query.search(q).with_entities(DocumentPage.id)
    counts = (
        DocumentPage.query.with_entities(DocumentPage.id)
        .filter(DocumentPage.id.in_(count_sq.subquery()))
        .join(Document)
        .group_by(Document.year, Document.jurisdiction)
        .values(Document.jurisdiction, Document.year, func.count(DocumentPage.id))
    )

    results = defaultdict(lambda: defaultdict(lambda: 0))

    # -2: no reports were published
    # -1: we don't have the published report

    for k, v in report_info["start_year"].items():
        for y in range(min_year, max_year + 1):
            results[k][y] = 0
        for y in range(min_year, v):
            results[k][y] = -2

    for k, v in report_info["no_reports"].items():
        # not sure about this?
        for y in range(min_year, max_year + 1):
            if (
                results[k][y] != -2
                and 0
                == Document.query.filter(
                    Document.jurisdiction == k, Document.year == y
                ).count()
            ):
                results[k][y] = -1
        for y in v:
            if max_year >= y >= min_year:
                results[k][y] = -2

    for c in counts:
        results[c[0]][c[1]] = c[2]

    if to_csv:
        csv_results = ["juris;year;count"]
        for k1, k2v in results.items():
            for k2, v in k2v.items():
                csv_results.append(";".join([k1, str(k2), str(v)]))

        return (
            "\n".join(csv_results),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    else:
        return jsonify(results)


# text files


@app.route("/<jurisdiction>-<int:year>.txt")
@cache.cached()
def text_details(jurisdiction, year):
    jurisdiction = jurisdiction.title()
    d = Document.query.filter_by(jurisdiction=jurisdiction, year=year).first()
    if d is None:
        abort(404)
    return (
        "\n\n\n".join([x.content for x in d.pages]),
        200,
        {
            "Content-Type": "text/plain; charset=utf-8",
            "X-Robots-Tag": "noindex, nofollow",
        },
    )


@app.after_request
def add_headers(response):
    headers = [
        ["Cache-Control", "public, max-age=604800"],
        ["Strict-Transport-Security", "max-age=31536000; includeSubdomains; preload"],
        ["X-Frame-Options", "SAMEORIGIN"],
        ["X-Content-Type-Options", "nosniff"],
        [
            "Content-Security-Policy",
            "default-src 'self'; object-src 'none'; form-action 'self' https://listen.daten.cool; font-src *;img-src * data:; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://matomo.daten.cool; style-src 'self' 'unsafe-inline'; connect-src 'self' https://matomo.daten.cool",
        ],
        ["X-XSS-Protection", "1; mode=block"],
        ["Referrer-Policy", "strict-origin"],
        [
            "Onion-Location",
            "http://zq5xve7vxljrsccptc4wxmuebnuiglhylahfwahyw7dzlxc43em4w6yd.onion"
            + request.full_path,
        ],
    ]

    for x in headers:
        response.headers[x[0]] = x[1]

    return response
