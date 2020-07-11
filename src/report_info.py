title = {
    "Sachsen-Anhalt": {1992: {"title": "1992/1993"}},
    "Thüringen": {2015: {"title": "2014/2015"}},
    "Niedersachsen": {1984: {"title": "1983/1984"}},
    "Bund": {1970: {"title": "1969/1970"}},
}

start_year = {
    "Sachsen-Anhalt": 1992,
    "Thüringen": 1991,
    "Niedersachsen": 1984,
    "Hamburg": 1993,
    "Bremen": 2002,
    "Berlin": 1990,
    "Bund": 1968,
    "Baden-Württemberg": 1975,
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
    "Baden-Württemberg": [],
    "Bayern": [],
    "Brandenburg": [],
    "Hessen": [1991, 1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999],
    "Mecklenburg-Vorpommern": [],
    "Saarland": [],
    "Schleswig-Holstein": [],
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

report_info = {
    "title": title,
    "start_year": start_year,
    "no_reports": no_reports,
    "abr": abr,
}

