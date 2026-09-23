# Jahresnachtrag neuer Berichte

Wie die Berichte eines neuen Berichtsjahres ins Archiv kommen.

## Wann die Berichte erscheinen

Die 17 Berichte eines Berichtsjahres erscheinen über das Folgejahr verteilt.
Ein Nachtrag ist deshalb immer ein Teil-Nachtrag; ein zweiter Durchgang ab
September ist nötig.

- Juni bis Anfang Juli: Bund und die meisten Länder.
- Regelmäßige Nachzügler bis September/Oktober: BW, HE, SL, TH.
- Das Saarland veröffentlicht keinen „Verfassungsschutzbericht“, sondern ein
  „Lagebild Verfassungsschutz“ — wer nach dem Titel sucht, findet es nicht.
- Berlin und Brandenburg veröffentlichen eine „Pressefassung“; sie ist das, was
  ins Archiv kommt. Sie ist oft zuerst über die Pressemitteilung verlinkt,
  bevor die Übersichtsseite des Landes aktualisiert ist.

## Dateien vorbereiten

Dateinamen: `vsbericht-<kürzel>-<jahr>.pdf`, der Bundesbericht ohne Kürzel
(`vsbericht-<jahr>.pdf`). Die Kürzel stehen in
[src/report_info.py](../src/report_info.py). Dateien mit der Endung `_en`,
`kurzfassung` oder `_parl` im Namen überspringt die Ingestion.

Arbeitsordner, jeweils mit absolutem Pfad und ohne Schrägstrich am Ende:

- `<ordner>.raw/` — die Originale, unverändert
- `<ordner>/` — Kopien, die in die Pipeline gehen

Vor der Pipeline:

- **Verschlüsselte PDFs** (z. B. AES-256 mit Owner-Passwort) lehnt `ocrmypdf`
  ab. Mit pikepdf entschlüsseln, das Original bleibt in `<ordner>.raw/`:

  ```bash
  docker run --rm -v "$DIR:/data" --entrypoint python3 jbarlow83/ocrmypdf \
    -c "import pikepdf; pikepdf.open('/data/x.pdf').save('/data/x.dec.pdf')"
  ```

- **Doppelseiten**: Manche Länder veröffentlichen zwei Seiten pro PDF-Seite
  (Querformat). `pdfinfo` zeigt nur die erste Seite; `mutool pages` über alle
  Seiten laufen lassen und nach Querformat suchen. Solche Dateien vor der
  Pipeline mit `wrangle_pdf/split_double_pages.sh <datei.pdf>` aus dem
  pdf-scripts-Repo teilen; es teilt nur die Querformatseiten und schreibt
  `<datei>.pdf.final.pdf`.

## Verarbeiten und hochladen

```bash
scripts/new_docs.sh /abs/pfad/<ordner> process   # Pipeline nach <ordner>.done/
scripts/new_docs.sh /abs/pfad/<ordner> upload    # Upload, dann update_docs.sh
```

`upload` ruft selbst `scripts/update_docs.sh` auf (`update-docs`,
`clear-cache`, `create-zips`). Der OCR-Schritt meldet bei digitalen PDFs „not
a scanned PDF“ und wird übersprungen — das ist korrekt.

## Vor dem Upload prüfen

Die Pipeline kann sporadisch Schriften und ToUnicode-Tabellen zerstören: Text
wird zu U+FFFD, Glyphen erscheinen als Kästchen. Ein erneuter Lauf auf
dieselbe Eingabe liefert meist eine saubere Datei. Eine kaputte Datei
verdirbt PDF, Seitenbilder und Suchindex zugleich. Deshalb jede Datei in
`<ordner>.done/` prüfen:

```bash
mutool draw -F text -o - datei.pdf | grep -o '�' | wc -l   # muss ~0 sein
mutool draw -o p.png -r 72 datei.pdf 10                    # Stichprobe ansehen
qpdf --check datei.pdf
```

Außerdem: Seitenzahl vor und nach der Pipeline gleich, und Textextraktion auf
einer Inhaltsseite funktioniert (die Volltextsuche hängt an `pdftotext`).

## Einen Bericht ersetzen

Für einen kaputten oder nachträglich geteilten Bericht:

1. Pipeline auf das Original neu laufen lassen, prüfen, die Kopie in
   `<ordner>.done/` ersetzen.
2. Alten Eintrag entfernen — `remove-docs` braucht den vollen Dateinamen:
   `flask remove-docs 'vsbericht-st-2025.pdf'`
3. Neu hochladen und gezielt einlesen:
   `flask update-docs 'vsbericht-st-2025'`, danach `clear-cache` und
   `create-zips`.

Seitenbilder und Wortpositionen werden dabei neu erzeugt; hat die neue Datei
mehr Seiten, überschreibt sie alle alten Bilder.

Gezieltes Einlesen ist schneller als `'*'`, etwa `flask update-docs
'vsbericht-*-2025'`. Bereits vorhandene Dokumente lehnt `update-docs` in
beiden Fällen ab (`file_url` ist eindeutig).
