import json
import os
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote, unquote

import click
import pdftotext

import cleantext
import spacy
from flask import (
    Flask,
    jsonify,
    make_response,
    render_template,
    request,
    send_from_directory,
    abort,
)
from flask_caching import Cache
from flask_sqlalchemy import BaseQuery, SQLAlchemy
from pdf2image import convert_from_path
from PIL import Image
from sqlalchemy import func
from sqlalchemy.sql import text
from sqlalchemy_searchable import SearchQueryMixin, make_searchable
from sqlalchemy_utils.types import TSVectorType

from report_info import report_info

app = Flask(__name__)

# caching at browser & nginx cache
@app.after_request
def add_header(response):
    response.cache_control.max_age = 60 * 60 * 24 # 1 day
    response.cache_control.public = True
    return response

if app.debug:
    url = "postgresql+psycopg2://postgres:password@db:5432/postgres"
    time.sleep(10)
    app.config["CACHE_TYPE"] = "null"
else:
    url = os.environ["DATABASE_URL"]
    app.config["CACHE_TYPE"] = "redis"
    app.config["CACHE_REDIS_URL"] = os.environ["REDIS_URL"]
    app.config["CACHE_DEFAULT_TIMEOUT"] = 60 * 60 * 24 * 14  # 2 weeks

app.config["SQLALCHEMY_DATABASE_URI"] = url

# remove whitespaces from HTML
app.jinja_env.trim_blocks = True
app.jinja_env.lstrip_blocks = True


cache = Cache(app)

db = SQLAlchemy(app)

make_searchable(db.metadata, options={"regconfig": "pg_catalog.german"})


class DocumentQuery(BaseQuery, SearchQueryMixin):
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
# db.create_all()
db.session.commit()


abr = [x.split() for x in Path("abr.txt").read_text().split("\n")]
jurisdictions = ["Bund"] + [l[1] for l in abr]

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


def proc_pdf(pdf_path):
    # no engl for now, no kurzfassung
    if pdf_path.stem.endswith("_en") or pdf_path.stem.endswith("kurzfassung"):
        return

    juris = "Bund"
    for [a, b] in abr:
        if a.lower() == str(pdf_path.name.split("-")[1]):
            juris = b
    year = int(pdf_path.stem.split("-")[-1])

    doc = Document(
        year=year,
        jurisdiction=juris,
        title=f"Verfassungsschutzbericht {year}",
        file_url="/pdfs/" + pdf_path.name,
    )

    print(pdf_path)

    db.session.add(doc)
    db.session.commit()

    with open(pdf_path, "rb") as f:
        pdf = pdftotext.PDF(f)
        num_pages = 0
        texts = []
        for i, page_text in enumerate(pdf):
            page_text = cleantext.clean(
                page_text, lang="de", lower=False, no_line_breaks=True
            )
            page_text = special_pdf_preproc(page_text)

            texts.append(page_text)
            num_pages += 1
            print(i)
            images = convert_from_path(str(pdf_path), first_page=i + 1, last_page=i + 1)

            fname = "/data" + "/images/" + pdf_path.stem + "_" + str(i) + ".jpg"
            img = images[0]
            basewidth = 900

            # resize to 900px width
            if img.size[0] > basewidth:
                wpercent = basewidth / float(img.size[0])
                hsize = int((float(img.size[1]) * float(wpercent)))
                img = img.resize((basewidth, hsize), Image.ANTIALIAS)
            img.save(fname, optimize=True)

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
def clear_cache():
    cache.clear()


@app.cli.command()
@click.argument("pattern")
def update_docs(pattern="*"):
    # todo: update or remove existing objects
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
        # fucked up cascade
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
def init_docs():
    # delete all data and caches
    db.drop_all()
    db.session.commit()

    cache.clear()

    db.configure_mappers()  # very important!
    db.create_all()
    db.session.commit()

    for pdf_path in Path("/data/pdfs").glob("*.pdf"):
        proc_pdf(pdf_path)


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
    return render_template("trends.html", qs=qs)


@app.route("/impressum")
@cache.cached()
def impressum():
    return render_template("impressum.html")


@app.route("/suche")
@cache.cached(query_string=True)
def search():
    q = request.args.get("q")
    if q is None or len(q) == 0:
        return render_template("search.html", q=None)
    q = cleantext.clean(q, lang="de")
    query, page, jurisdiction, max_year, min_year = build_query()

    results = query.search(q, sort=True).paginate(page, 20, True).items

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
        snips = db.engine.execute(
            text(
                f"SELECT id, ts_headline(content, tsq_parse('{q}'), 'MaxFragments=10, MinWords=5, MaxWords=20, FragmentDelimiter=XXX.....XXX') as text FROM {DocumentPage.__tablename__} WHERE id in ({ids})"
            )
        )
    else:
        snips = []

    for s in snips:
        results[ids_int.index(s.id)].snips = s.text.split("XXX.....XXX")

    return render_template(
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


@app.route("/robots.txt")
@cache.cached()
def static_from_root():
    return send_from_directory(app.static_folder, request.path[1:])


# FILES
# ensure the files are served by nginx


@app.route("/pdfs/<path:filename>")
def download_pdf(filename):
    if app.debug:
        return send_from_directory("/data/pdfs", filename)

    response = make_response()
    response.headers["Content-Type"] = "application/pdf"
    response.headers["X-Accel-Redirect"] = "/x_pdfs/" + filename
    return response


@app.route("/images/<path:filename>")
def download_img(filename):
    if app.debug:
        return send_from_directory("/data/images", filename)

    response = make_response()
    response.headers["X-Accel-Redirect"] = "/x_images/" + filename
    return response


# API


def serialize_doc(d):
    return {
        "year": d.year,
        "title": d.title,
        "jurisdiction": d.jurisdiction,
        "file_url": request.base_url[:-1] + d.file_url,
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
            res = (
                TokenCount.query.filter(TokenCount.token == t)
                .with_entities(TokenCount.document_id)
                .all()
            )
            if ids is None:
                ids = set(res)
            else:
                ids = ids.intersection(res)
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
# @cache.cached(query_string=True)
def api_mentions():
    q = request.args.get("q")

    to_csv = not request.args.get("csv") is None

    if q is None or len(q) == 0:
        abort(404)
    q = cleantext.clean(q, lang="de")
    query, page, jurisdiction, max_year, min_year = build_query()

    if max_year is None:
        max_year = 2018
    if min_year is None:
        min_year = 1993

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

    for k, v in report_info['start_year'].items():
        for y in range(min_year, max_year + 1):
            results[k][y] = 0
        for y in range(min_year, v):
            results[k][y] = -1
    
    for k, v in report_info['no_reports'].items():
        for y in v:
            if max_year >= y >= min_year:
                results[k][y] = -1
        for y in range(min_year, max_year + 1):
            if 0 == Document.query.filter(Document.jurisdiction == k, Document.year == y).count():
                results[k][y] = -1

    for c in counts:
        results[c[0]][c[1]] = c[2]

    if to_csv:
        csv_results = ['juris;year;count']
        for k1, k2v in results.items():
            for k2, v in k2v.items():
                csv_results.append(';'.join([k1, str(k2), str(v)]))

        return (
            "\n".join(csv_results),
            200,
            {"Content-Type": "text/plain; charset=utf-8"},
        )
    else:
        return jsonify(results)
    # c_d = {}
    # for c in counts:
    #     c_d[c[0]] = c[1]
    # counts = json.dumps(c_d)



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
        {"Content-Type": "text/plain; charset=utf-8"},
    )
