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
2. clone repository and go to its root
3. `docker-compose up`
4. http://localhost:5000

## Production

Deploy with [Dokku](https://github.com/dokku/dokku).

1. create a Dokku app
2. link a postgres db
3. link a redis cache
4. Then mount two folders for the static content:

- folder with pdfs to `/data/pdfs`
- folder with resulting images to `/data/imgs`

To serve the images and pdfs via nginx (xsendfile), adapt the nginx config:

```bash
location /x_images {
  internal;
  alias /folder/with/images;
}

location /x_pdfs {
  internal;
  alias /folder/with/pdfs;
}
```

## One-off commands

- clear cache: `dokku run the-app flask clear-cache`
- add documents: `dokku run the-app flask update-docs '*'`

## PDF preprocessing

All documents should be PDF in a A4/A5 portrait format. Several helper scripts exists but occasionally, manual work is required.

Two folders exists:

- 'raw', sometimes the original PDF requires manual help (e.g. some pages are in landscape format)
- 'cleaned', normalized PDFs, but before the OCR & file reduction

Naming: `vsbericht-nw-2000.pdf` for NRW 2000, `vsbericht-2000.pdf` for the federal report 2000.

If a report is for multiple years, choose the latest year as the main date. And update <src/report_info.py> accordingly.

## Search

Using Postgres' full-text search features via [sqlalchemy-searchable](https://github.com/kvesteri/sqlalchemy-searchable). Some shortcomings, though. Right now, it's not possible to use trigram similarity. And wildcard queries are the default and can only be deactivated via quotes, i.e., "query". Also the results are not shown on the PDFs

## License

MIT.
