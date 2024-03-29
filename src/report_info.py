# document various information (and special cases) about the reports

title = {
    "Sachsen-Anhalt": {1992: {"title": "1992/1993"}},
    "Thüringen": {2015: {"title": "2014/2015"}},
    "Niedersachsen": {1984: {"title": "1983/1984"}},
    "Bund": {1970: {"title": "1969/1970"}},
    "Schleswig-Holstein": {1985: {"title": "1985/1986"}},
    "Baden-Württemberg": {1976: {"title": "1976/1977"}, 1975: {"title": "1975/1976"}},
}

start_year = {
    "Sachsen-Anhalt": 1992,
    "Thüringen": 1992,
    "Niedersachsen": 1984,
    "Hamburg": 1993,
    "Bremen": 2002,
    "Berlin": 1990,
    "Bund": 1968,
    "Baden-Württemberg": 1973,
    "Bayern": 1976,
    "Brandenburg": 1993,
    "Hessen": 1977,
    "Mecklenburg-Vorpommern": 1992,
    "Saarland": 2013,
    "Schleswig-Holstein": 1976,
    "Nordrhein-Westfalen": 1950,
    "Sachsen": 1993,
    "Rheinland-Pfalz": 1984,
}

no_reports = {
    "Sachsen-Anhalt": [],
    "Thüringen": [2014],
    "Niedersachsen": [],
    "Hamburg": [],
    "Bremen": [],
    "Berlin": [],
    "Bund": [1969],
    "Baden-Württemberg": [1977],
    "Bayern": [],
    "Brandenburg": [],
    "Hessen": [1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999],
    "Mecklenburg-Vorpommern": [],
    "Saarland": [],
    "Schleswig-Holstein": [1986],
    "Nordrhein-Westfalen": [],
    "Sachsen": [],
    "Rheinland-Pfalz": [],
}

abr_text = """BW 	Baden-Württemberg
BY 	Bayern
BE 	Berlin
BB 	Brandenburg
HB 	Bremen
HH 	Hamburg
HE 	Hessen
MV 	Mecklenburg-Vorpommern
NI 	Niedersachsen
NW 	Nordrhein-Westfalen
RP 	Rheinland-Pfalz
SL 	Saarland
SN 	Sachsen
ST 	Sachsen-Anhalt
SH 	Schleswig-Holstein
TH 	Thüringen"""

abr = [x.split() for x in abr_text.split("\n")]


changes = {
    "Bayern": {
        2019: [
            (
                "Verwaltungsgericht München: Zeitgeschichtliche Forschungsstelle Ingolstadt (ZFI) nicht rechtsextrem",
                "https://web.archive.org/web/20200723110136/https://www.br.de/nachrichten/bayern/gericht-stoppt-bayerischen-verfassungsschutzbericht,S5P3sJi",
            )
        ]
    }
}

comments = {
    "Sachsen-Anhalt": {
        2012: [
            "Auf PDF-Seite 61 & 187 wurde eine Person anonymisert, die nur aufgrund einer Verwechselung in dem Bericht landete."
        ]
    }
}

report_info = {
    "title": title,
    "start_year": start_year,
    "no_reports": no_reports,
    "abr": abr,
    "changes": changes,
    "comments": comments,
}
