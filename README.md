<img src="https://verfassungsschutzberichte.de/static/thumbnail.jpg">

# Verfassungsschutzberichte.de

> Über was informiert der Verfassungs­schutz? Die Berichte des Geheimdienstes: gesammelt, durchsuchbar und analysiert.

> Der Verfassungsschutz hat die Aufgabe die Öffentlichkeit über verfassungsfeindliche Bestrebungen aufzuklären. Die 16 Landesämter und das Bundesamt für Verfassungsschutz veröffentlichen jährlich Verfassungsschutzberichte. Diese Webseite ist ein zivilgesellschaftliches Archiv, das den Zugang zu den Berichten erleichert.

- Spiegel Online: [„Netzaktivist startet Archiv für Verfassungsschutzberichte“](https://www.spiegel.de/netzwelt/web/netzaktivist-startet-online-archiv-fuer-verfassungsschutzberichte-a-1294435.html)
- Netzpolitik.org: [„Wo der Verfassungsschutz hinschaut“](https://netzpolitik.org/2019/wo-der-verfassungsschutz-hinschaut/)
- golem.de: [„Portal macht Verfassungsschutzberichte durchsuchbar“](https://www.golem.de/news/open-data-portal-macht-verfassungsschutzberichte-durchsuchbar-1911-144768.html)
- [Unsere Pressemitteilung zum Launch](https://codefor.de/blog/Launch-Verfassungsschutzberichte.de.html)

## English

> About what does the _Verfassungsschutz_ (the German internal intelligence, translated: protection of the constitution) inform? The reports of the secret service: collected, searchable and analyzed.

> The _Verfassungsschutz_ has the task of informing the public about anti-constitutional efforts. The 16 state offices and the federal office publish annual reports on the protection of the constitution. This website is a civil society archive that simplifies access to the reports.

## Development

1. install and run [Docker](https://www.docker.com/)
2. `git clone https://github.com/dmedak/verfassungsschutzberichte.de && cd verfassungsschutzberichte.de`
3. `docker-compose up`
4. http://localhost:5000

### Add PDFs for Development

To get started, put some PDFs in to `verfassungsschutzberichte.de/data/pdfs` and create the folder `verfassungsschutzberichte.de/data/images`.
Then get the container id with `docker ps`, then enter the Docker container `docker exec -it f00d7aa42de8 bash` with the appropriate id. Finally run `flask update-docs '*'` inside the container to process PDFs.

### Testing

End-to-end tests verify that the application works correctly after updates (e.g., Python version upgrades).

**Run tests locally:**
```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run tests (requires Docker)
./scripts/run_tests.sh
```

**Or manually:**
```bash
# Start services
docker compose up -d

# Wait for app to be ready, then run tests
TEST_BASE_URL=http://localhost:5000 pytest tests/ -v

# Stop services
docker compose down
```

**CI/CD:**
Tests run automatically on every push and pull request via GitHub Actions.

## Production

Deploy with [Dokku](https://github.com/dokku/dokku).

1. create a Dokku app, e.g. with the name `vsb`
2. link a Postgres db
3. link a Redis cache
4. Then mount a folder `data` with contains two folders (`pdfs` for PDFs and `images` for images of the PDF pages) for the static content: `dokku storage:mount $app $path:/data/`

To serve the images and PDFs via nginx (xsendfile), adapt the nginx config of Dokku (e.g. create `/home/dokku/vsb/nginx.conf.d/myconf.conf`):

```
location /x_images {
  internal;
  add_header X-Robots-Tag "noindex, nofollow"; # prevent search enginges from indexing files
  alias /folder/with/images;
}

location /x_pdfs {
  internal;
  add_header X-Robots-Tag "noindex, nofollow";
  alias /folder/with/pdfs;
}
```

Adjust the Postgres config and increase `shared_buffers` and `work_mem` to, e.g., `1GB` and `128MB` respectively.

## One-off commands

- clear cache: `dokku run vsb flask clear-cache`
- add documents: `dokku run vsb flask update-docs '*'`
- remove all documents: `dokku run vsb flask remove-docs '*'`
- remove one document: `dokku run vsb flask remove-docs 'vsbericht-th-2002.pdf'`
- clean all data from the database and adds all documents again: `dokku run vsb clear-data`

## Data Storage

The reports are organized by folders and filenames.
This has the limitation that we can't store different versions of a yearly report.

### PDF preprocessing

All documents should be PDF in a A4/A5 portrait format.
Several pdf scripts exists but occasionally, manual work is required.
See [scripts](scripts).

### Folder Structures

Two folders exists to store the PDFs:

- `raw`, sometimes the original PDF requires manual help (e.g. some pages are in landscape format)
- `cleaned`, normalized PDFs, but before the OCR & file reduction

### Adding a New Report

Naming: `vsbericht-nw-2000.pdf` for NRW 2000, `vsbericht-2000.pdf` for the federal report 2000.

If a report is for multiple years, choose the latest year as the main date.

And update the title in [src/report_info.py](src/report_info.py) accordingly.

1. Put the file in a folder, e.g. `x`
2. cd `scripts`
3. `./new_docs.sh /absolute/path/x process`
4. verify the result in `x.done` is fine, optionally add a `x.raw` folder with the unprocessed files.
5. `./new_docs.sh /absolute/path/x upload`

## Search

Using Postgres' full-text search features via [sqlalchemy-searchable](https://github.com/kvesteri/sqlalchemy-searchable).
Right now, there are some shortcomings.
It's not possible to use trigram similarity.
And wildcard queries are the default and can only be deactivated by using quotes, i.e., "query".
Also the matching tokens are not displayed on the page/image.
Further work is required to improve the search.

## License

MIT
