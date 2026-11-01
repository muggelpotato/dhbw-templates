"""Formatvorlagen, Listen, Standards und Design der Vorlage als XML."""
import zlib
from pathlib import Path
from string import Template
from xml.sax.saxutils import escape

from paket import MC, MSWORD, W, element, schalter, stil_id
from spez import umrechnen

DESIGN = Path(__file__).with_name("design.xml")
TYP = {"Absatz": "paragraph", "verknüpft": "paragraph", "Zeichen": "character",
       "Tabelle": "table", "Liste": "numbering"}
VERKNUEPFT = "Char"  # Words Endung für die Kennung der verknüpften Zeichenvorlage
LATENT = {"defLockedState": 0, "defUIPriority": 99, "defQFormat": 0, "count": 376}
STUFE = 1440 // 4  # Words Einzug je Ebene einer neuen Liste, ein Viertelzoll
AN, AUS = {"ja": None, "nein": 0}, {"ja": 0, "nein": None}
AUSGEBLENDET = {"nein": {}, "ja": {"semiHidden": True, "unhideWhenUsed": True},
                "immer": {"semiHidden": True}}
JC = {"links": "left", "zentriert": "center", "rechts": "right", "Blocksatz": "both"}
TAB = {"links": "left", "zentriert": "center", "rechts": "right", "dezimal": "decimal",
       "gelöscht": "clear"}
FUELL = {"Punkte": "dot", "Striche": "hyphen", "Linie": "underscore"}
EBENE = {str(ebene + 1): ebene for ebene in range(9)}
ZAHLART = {"arabisch": "decimal", "römisch groß": "upperRoman", "römisch klein": "lowerRoman",
           "Buchstaben groß": "upperLetter", "Buchstaben klein": "lowerLetter",
           "Aufzählungszeichen": "bullet"}
SEITE = {"oben": "top", "links": "left", "unten": "bottom", "rechts": "right",
         "innenwaagrecht": "insideH", "innensenkrecht": "insideV"}
BEDINGUNG = {"kopf": "firstRow", "fuss": "lastRow", "erstespalte": "firstCol",
             "band1": "band1Horz", "band2": "band2Horz"}
DURCHGEHEND = ("rahmeninnensenkrecht",)  # gilt auch in Kopf, erster Spalte und Bändern
# Eigenschaften, die eine Formatvorlage mit listenebene an die Ebene ihrer Liste gibt
LAGE = ("einzuglinks", "erstzeile", "tabstopps")


def _schattierung(werte, s):
    return {"val": "clear", "color": "auto", "fill": werte.wert(s)}


def _farbe(werte, s):
    """Eine Farbe gleich der Designfarbe link folgt dem Design als hyperlink."""
    bezug = werte.wert(s) == werte.wert("dokument.designfarbe.link")
    return {"val": werte.wert(s), "themeColor": "hyperlink" if bezug else None}


def _linie(werte, s):
    """Linie mit rahmenfarbe und rahmenabstand derselben Formatvorlage, 0 für keine."""
    objekt, staerke = s.rpartition(".")[0], werte.mass(s, "achtelpunkt")
    abstand, farbe = f"{objekt}.rahmenabstand", werte.eigenschaften(objekt).get("rahmenfarbe")
    return {"val": "single", "sz": staerke,
            "space": werte.mass(abstand, "punkt") if abstand in werte else 0,
            "color": farbe or "auto"} if staerke else {"val": "none"}


def _tab(glied, nummer=False):
    """Tabstopp „Position Einheit Ausrichtung [Füllzeichen]“, für die Nummer nur die Position."""
    zahl, einheit, art, *fuell = glied.split()
    return element("tab", {"val": "num" if nummer else TAB[art],
                           "leader": FUELL[fuell[0]] if fuell and not nummer else None,
                           "pos": umrechnen(zahl, einheit, "twip")})


def _seiten(vorsilbe, pfad, umrechnung, *typ, zahl=len(SEITE)):
    """Ein Eintrag je Seite, etwa rahmenoben unter pPr/pBdr/top."""
    return [(vorsilbe + wort, f"{pfad}/{seite}", None, umrechnung, *typ)
            for wort, seite in list(SEITE.items())[:zahl]]


# Eigenschaft, Ort/Element, Attribut, Umrechnung und wahlweise die Typen, für die der Eintrag
# gilt; je Ort in Schemafolge. Die Umrechnung ist eine Einheit von Word, eine Tabelle der
# Wörter (None schreibt das Element ohne Attribut) oder eine Funktion; leer bleibt der Wert.
EIGENSCHAFT = (
    ("mitnaechstem", "pPr/keepNext", "val", AN),
    ("zusammenhalten", "pPr/keepLines", "val", AN),
    ("umbruchoberhalb", "pPr/pageBreakBefore", "val", AN),
    ("absatzkontrolle", "pPr/widowControl", "val", AN),
    ("listenebene", "pPr/numPr/ilvl", "val", EBENE),
    ("liste", "pPr/numPr/numId", None,
     lambda werte, s: {"val": _listennamen(werte).index(werte.wert(s)) + 1}),
    *_seiten("rahmen", "pPr/pBdr", _linie, "paragraph", zahl=4),
    ("schattierung", "pPr/shd", None, _schattierung, "paragraph"),
    ("tabstopps", "pPr/tabs", None,
     lambda werte, s: "".join(map(_tab, werte.liste(s))), "paragraph table"),
    ("tabstopps", "pPr/tabs", None, lambda werte, s: _tab(werte.liste(s)[0], nummer=True), "lvl"),
    ("silbentrennung", "pPr/suppressAutoHyphens", "val", AUS),
    ("abstandvor", "pPr/spacing", "before", "twip"),
    ("abstandnach", "pPr/spacing", "after", "twip"),
    ("zeilenabstand", "pPr/spacing", None,
     lambda werte, s: {"line": werte.mass(s, "zeile"), "lineRule": "auto"}),
    ("einzuglinks", "pPr/ind", "left", "twip"),
    ("einzugrechts", "pPr/ind", "right", "twip"),
    ("erstzeile", "pPr/ind", None, lambda werte, s: {
        "hanging" if werte.zahl(s) < 0 else "firstLine": abs(werte.mass(s, "twip"))}),
    ("gleichohneabstand", "pPr/contextualSpacing", "val", AN),
    ("ausrichtung", "pPr/jc", "val", JC),
    ("gliederungsebene", "pPr/outlineLvl", "val", EBENE | {"Textkörper": 9}),
    ("schriftart", "rPr/rFonts", "ascii", ""),
    ("schriftart", "rPr/rFonts", "hAnsi", ""),
    ("fett", "rPr/b", "val", AN),
    ("kursiv", "rPr/i", "val", AN),
    ("versalien", "rPr/caps", "val", AN),
    ("kapitaelchen", "rPr/smallCaps", "val", AN),
    ("rechtschreibung", "rPr/noProof", "val", AUS),
    ("farbe", "rPr/color", None, _farbe),
    ("laufweite", "rPr/spacing", "val", "twip"),
    ("unterschneidung", "rPr/kern", "val", "halbpunkt"),
    ("schriftgroesse", "rPr/sz", "val", "halbpunkt"),
    ("schriftgroesse", "rPr/szCs", "val", "halbpunkt", "standard"),
    ("unterstrichen", "rPr/u", "val", {"ja": "single", "nein": "none"}),
    ("schattierung", "rPr/shd", None, _schattierung, "character"),
    ("hochgestellt", "rPr/vertAlign", "val", {"ja": "superscript", "nein": "baseline"}),
    ("sprache", "rPr/lang", "val", ""),
    ("baenderung", "tblPr/tblStyleRowBandSize", "val", {"ja": 1, "nein": 0}),
    ("tabellenausrichtung", "tblPr/jc", "val", JC),
    *_seiten("rahmen", "tblPr/tblBorders", _linie, "table"),
    *_seiten("zellenrand", "tblPr/tblCellMar",
             lambda werte, s: {"w": werte.mass(s, "twip"), "type": "dxa"}, zahl=4),
    ("zeilenumbruch", "trPr/cantSplit", "val", AUS),
    *_seiten("rahmen", "tcPr/tcBorders", _linie, "tblStylePr"),
    ("schattierung", "tcPr/shd", None, _schattierung, "table tblStylePr"),
    ("zellausrichtung", "tcPr/vAlign", "val",
     {"oben": "top", "Mitte": "center", "unten": "bottom"}),
)


def _baum(knoten):
    """Elemente aus Pfaden je Name der obersten Stufe, Geschwister in der Folge ihrer Pfade."""
    gruppen = {}
    for pfad, wert in knoten.items():
        name, _, rest = pfad.partition("/")
        gruppen.setdefault(name, {})[rest] = wert
    elemente = {}
    for name, kinder in gruppen.items():
        attribute, inhalt = kinder.pop("", ({}, ""))
        elemente[name] = element(name, attribute, inhalt + "".join(_baum(kinder).values()))
    return elemente


def _eigenschaften_xml(werte, schluessel, typ):
    """w:pPr, w:rPr, w:tblPr, w:trPr und w:tcPr je Ort aus dem Schlüssel je Eigenschaft."""
    knoten = {}
    for eigenschaft, pfad, attribut, umrechnung, *typen in EIGENSCHAFT:
        s = schluessel.get(eigenschaft)
        if s is None or typen and typ not in typen[0].split():
            continue
        if callable(umrechnung):
            neu = umrechnung(werte, s)
        elif isinstance(umrechnung, dict):
            neu = {attribut: werte.nach(s, umrechnung)}
        else:
            neu = {attribut: werte.mass(s, umrechnung) if umrechnung else werte.wert(s)}
        attribute, inhalt = knoten.get(pfad, ({}, ""))
        knoten[pfad] = ((attribute, inhalt + neu) if isinstance(neu, str)
                        else (attribute | neu, inhalt))
    return _baum(knoten)


def plan(werte):
    """Felder und Soll je Formatvorlage des Bestands."""
    return [reihe | {"soll": werte.eigenschaften(f"stil.{reihe['kennung']}")}
            for reihe in werte.bestand("formatvorlagen")]


def _bedingungen(werte, schluessel):
    """Bedingte Formate einer Tabellenvorlage aus den Eigenschaften mit ihrer Vorsilbe."""
    durchgehend = {name: schluessel[name] for name in DURCHGEHEND if name in schluessel}
    formate = ""
    for vorsilbe, art in BEDINGUNG.items():
        eigene = {eigenschaft.removeprefix(vorsilbe): s for eigenschaft, s in schluessel.items()
                  if eigenschaft.startswith(vorsilbe)}
        if _eigenschaften_xml(werte, eigene, "tblStylePr"):
            kinder = _eigenschaften_xml(werte, durchgehend | eigene, "tblStylePr")
            formate += f'<w:tblStylePr w:type="{art}">{"".join(kinder.values())}</w:tblStylePr>'
    return formate


def _stil_xml(werte, eintrag, partner):
    kennung, soll, typ = eintrag["kennung"], eintrag["soll"], TYP[eintrag["art"]]
    # Nummer und Lage einer Ebene stehen in der Liste, nicht in der Formatvorlage
    ohne = LAGE if "listenebene" in soll else ()
    schluessel = {name: f"stil.{kennung}.{name}" for name in soll if name not in ohne}
    kopf = {"name": eintrag["name"], "basedOn": stil_id(soll.get("basis", "")),
            "next": stil_id(soll.get("folgevorlage", "")), "link": stil_id(partner),
            "autoRedefine": soll.get("aktualisieren") == "ja",
            "uiPriority": soll.get("prioritaet"), **AUSGEBLENDET[soll.get("ausgeblendet", "nein")],
            "qFormat": soll.get("galerie") == "ja"}
    kinder = _eigenschaften_xml(werte, schluessel, typ)
    bedingt = _bedingungen(werte, schluessel) if typ == "table" else ""
    inhalt = "".join(schalter(*paar) for paar in kopf.items()) + "".join(kinder.values())
    # w:default und w:customStyle setzt Word beim Speichern selbst
    return f'<w:style w:type="{typ}" w:styleId="{stil_id(kennung)}">{inhalt}{bedingt}</w:style>'


def _standards(werte):
    """w:docDefaults nach dokument.standard, w:latentStyles nur als Kopf."""
    objekt = "dokument.standard"
    schluessel = {name: f"{objekt}.{name}" for name in werte.eigenschaften(objekt)}
    kinder = _eigenschaften_xml(werte, schluessel, "standard")
    verborgen = 0 if werte.ja("dokument.einstellung.latentkatalog") else 1
    latent = LATENT | {"defSemiHidden": verborgen, "defUnhideWhenUsed": verborgen}
    return (f'<w:docDefaults><w:rPrDefault>{kinder.get("rPr", "")}</w:rPrDefault>'
            f'<w:pPrDefault>{kinder.get("pPr", "")}</w:pPrDefault></w:docDefaults>'
            + element("latentStyles", latent))


def formatvorlagen(werte, eintraege):
    """styles.xml aus Standards, latenten und den Formatvorlagen aus plan."""
    paare = {eintrag["kennung"]: eintrag["kennung"] + VERKNUEPFT
             for eintrag in eintraege if eintrag["art"] == "verknüpft"}
    paare |= {zeichen: absatz for absatz, zeichen in paare.items()}
    stile = "".join(_stil_xml(werte, eintrag, paare.get(eintrag["kennung"], ""))
                    for eintrag in eintraege)
    return f'<w:styles xmlns:w="{W}">{_standards(werte)}{stile}</w:styles>'


def _listennamen(werte):
    """Namen der Listen in der Folge ihres ersten Auftretens im Bestand."""
    schluessel = (f"stil.{reihe['kennung']}.liste" for reihe in werte.bestand("formatvorlagen"))
    return list(dict.fromkeys(werte.wert(s) for s in schluessel if s in werte))


def _liste(werte, soll):
    """Liste einer Formatvorlage nach ihrem Soll, sonst die ihrer Basis."""
    return soll.get("liste") or _liste(werte, werte.eigenschaften(f"stil.{soll['basis']}"))


def _ebene_xml(werte, nr, eintrag):
    """Ebene einer Liste; ohne Formatvorlage ohne Nummer an Words Stelle."""
    if eintrag is None:
        nummer = '<w:numFmt w:val="none"/><w:lvlText w:val=""/>'
        lage = f'<w:pPr><w:ind w:left="{(nr + 1) * STUFE}" w:hanging="{STUFE}"/></w:pPr>'
    else:
        objekt = f"stil.{eintrag['kennung']}"
        nummer = (element("numFmt", {"val": werte.nach(f"{objekt}.nummernformat", ZAHLART)})
                  + element("pStyle", {"val": stil_id(eintrag["kennung"])})
                  + element("lvlText", {"val": werte.wert(f"{objekt}.nummer")}))
        schluessel = {name: f"{objekt}.{name}" for name in LAGE if name in eintrag["soll"]}
        lage = "".join(_eigenschaften_xml(werte, schluessel, "lvl").values())
    return (f'<w:lvl w:ilvl="{nr}"><w:start w:val="1"/>{nummer}<w:lvlJc w:val="left"/>{lage}'
            "</w:lvl>")


def listen(werte, eintraege):
    """numbering.xml: je Liste neun Ebenen mit ihren Formatvorlagen aus plan, dazu ihre Nummer."""
    abstrakt = nummern = ""
    for nr, name in enumerate(_listennamen(werte)):
        ebenen = {EBENE[eintrag["soll"]["listenebene"]]: eintrag for eintrag in eintraege
                  if "listenebene" in eintrag["soll"] and _liste(werte, eintrag["soll"]) == name}
        stufen = "".join(_ebene_xml(werte, ebene, ebenen.get(ebene)) for ebene in EBENE.values())
        vorlage = [eintrag["kennung"] for eintrag in eintraege
                   if eintrag["art"] == "Liste" and eintrag["soll"].get("liste") == name]
        bezug = (element("styleLink", {"val": stil_id(vorlage[0])}) if vorlage
                 else element("name", {"val": name}))
        nsid = zlib.crc32(name.encode())
        abstrakt += (f'<w:abstractNum w:abstractNumId="{nr}"><w:nsid w:val="{nsid:08X}"/>'
                     '<w:multiLevelType w:val="multilevel"/>'
                     f'<w:tmpl w:val="{zlib.crc32(stufen.encode()):08X}"/>{bezug}{stufen}'
                     '</w:abstractNum>')
        # Word schreibt durableId als positive Zahl unter 2^31
        nummern += (f'<w:num w:numId="{nr + 1}" w16cid:durableId="{nsid & 0x7FFFFFFF}">'
                    f'<w:abstractNumId w:val="{nr}"/></w:num>')
    return (f'<w:numbering xmlns:w="{W}" xmlns:mc="{MC}" mc:Ignorable="w16cid" '
            f'xmlns:w16cid="{MSWORD}/2016/wordml/cid">{abstrakt}{nummern}</w:numbering>')


def design(werte):
    """theme1.xml: Words Design mit Designschriften und Designfarben aus QUELLE."""
    ersatz = werte.eigenschaften("dokument.designfarbe") | {
        objekt: werte.wert(f"dokument.{objekt}.schriftart")
        for objekt in ("designueberschrift", "designtext")}
    vorlage = " ".join(DESIGN.read_text(encoding="utf-8").split()).replace("> <", "><")
    return Template(vorlage).substitute(
        {name: escape(text, {'"': "&quot;"}) for name, text in ersatz.items()})
