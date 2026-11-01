"""Absätze mit Läufen und Steuerelementen, Felder und Tabellen nach QUELLE als XML."""
import re
from itertools import batched, cycle, groupby
from operator import itemgetter
from xml.sax.saxutils import escape

import steuer
from paket import ACHTELZOLL, element, lauf, schalter, stil_id
from spez import WORD
from stile import JC, SEITE

KLAMMER = re.compile(r"\{([^{}]+)\}")
TEXTSCHLUESSEL = re.compile(r"text\.\w+\.\w+")
# Tabellenformatoptionen einer neuen Tabelle in Word: Kopfzeile, erste Spalte, Zeilenbänder
OPTIONEN = {"val": "04A0", "firstRow": 1, "lastRow": 0, "firstColumn": 1, "lastColumn": 0,
            "noHBand": 0, "noVBand": 1}
ENDE = lauf(inhalt=element("fldChar", {"fldCharType": "end"}))
FELDENDE = element("p", inhalt=ENDE)
# Baufunktion je Vorsilbe eines Einschubs außer text, gerufen mit Werten, Name, Stelle, Titelstil
EINSCHUB = {
    "angabe": steuer.angabe,
    "steuerelement": lambda werte, name, *_: steuer.frei(werte, name),
    "feld": lambda werte, name, *_: feld(werte.wert(f"feld.{name}.code")),
    "tab": lambda *_: lauf(inhalt=element("tab")),
    "seitenumbruch": lambda *_: lauf(inhalt=element("br", {"type": "page"})),
    "kaestchen": lambda werte, *_: steuer.kaestchen(werte, werte.wert("dokument.rolle.kaestchen")),
}


def absatz(stil="", inhalt="", eigenschaften=""):
    """Absatz w:p in stil, ohne stil in Normal.

    eigenschaften sind weitere Kinder von w:pPr in Words Folge hinter pStyle, etwa pBdr,
    spacing, ind, jc, rPr der Absatzmarke und sectPr; ohne beide fehlt w:pPr.
    """
    kopf = schalter("pStyle", stil_id(stil)) + eigenschaften
    return element("p", inhalt=(f"<w:pPr>{kopf}</w:pPr>" if kopf else "") + inhalt)


def text(werte, stil, wert, stelle, zeichenstil="", titelstil=""):
    return absatz(stil, laeufe(werte, wert, stelle, zeichenstil, titelstil))


def laeufe(werte, wert, stelle, zeichenstil="", titelstil=""):
    """Läufe und Steuerelemente zu wert, ein bloßer Textschlüssel gilt als {text.X}.

    Benachbarter Text, auch aus {text.X}, bildet einen Lauf in zeichenstil, Angaben in titelstil.
    """
    xml = ""
    for ist_text, gruppe in groupby(_stuecke(werte, wert, stelle, titelstil), itemgetter(0)):
        stuecke = "".join(stueck for _, stueck in gruppe)
        xml += lauf(stuecke, zeichenstil) if ist_text else stuecke
    return xml


def _stuecke(werte, wert, stelle, titelstil):
    """Paare aus Merker für Text und Stück in der Folge von wert."""
    teile = KLAMMER.split(f"{{{wert}}}" if TEXTSCHLUESSEL.fullmatch(wert) else wert)
    for wortlaut, einschub in zip(teile[::2], teile[1::2] + [""]):
        if wortlaut:
            yield True, wortlaut
        if einschub:
            yield from _einschub(werte, einschub, stelle, titelstil)


def _einschub(werte, einschub, stelle, titelstil):
    """Stücke eines Einschubs, {text.X.Y} ist eine Auswahl, wenn es text.auswahl.X gibt.

    Vor die Stelle kommen der Einschub und sein Objekt, bei {text.X} nur der Schlüssel.
    """
    vorsilbe, _, name = einschub.partition(".")
    genauer = (einschub, einschub.rpartition(".")[0], *stelle)
    if vorsilbe != "text":
        yield False, EINSCHUB[vorsilbe](werte, name, genauer, titelstil)
    elif f"text.auswahl.{name.partition('.')[0]}" in werte:
        yield False, steuer.auswahl(werte, einschub, genauer)
    else:
        yield from _stuecke(werte, werte.wert(einschub), (einschub, *stelle), titelstil)


def feld(code):
    """Komplexes Feld ohne Ergebnis, das setzt Word beim Aktualisieren."""
    befehl = f'<w:instrText xml:space="preserve"> {escape(code)} </w:instrText>'
    return "".join(lauf(inhalt=teil) for teil in (
        element("fldChar", {"fldCharType": "begin"}), befehl,
        element("fldChar", {"fldCharType": "separate"}))) + ENDE


def verzeichnis(code, stil):
    """Verzeichnisfeld in zwei Absätzen in stil, das Feldende im eigenen."""
    return absatz(stil, feld(code).removesuffix(ENDE)) + absatz(stil, ENDE)


def tabelle(werte, objekt, zellstil, stelle):
    """Tabelle nach objekt: Zellen aus inhalt oder kopf und zeilen, je Spalte eine Breite.

    Jede Zelle steht in ihrem Glied von stile, ohne stile in zellstil und Zeile 1 in kopfstil;
    mit kopfwiederholen wiederholt Word Zeile 1 auf jeder Seite.
    """
    breiten = werte.masse(f"{objekt}.spaltenbreiten", "twip")
    eintraege = _zellen(werte, objekt, len(breiten))
    if len(eintraege) % len(breiten):
        raise ValueError(f"{objekt}: {len(eintraege)} Zellen füllen keine ganzen Zeilen "
                         f"aus {len(breiten)} Spalten nach {objekt}.spaltenbreiten")
    eigen = werte.eigenschaften(objekt)
    kopfstil = eigen.get("kopfstil", zellstil)
    paare = werte.paare(f"{objekt}.stile", f"{objekt}.inhalt") if "stile" in eigen else [
        (kopfstil if nr < len(breiten) else zellstil, wert) for nr, wert in enumerate(eintraege)]
    rand = _zellenrand(werte, objekt)
    spalten = [element("tcPr", inhalt=element("tcW", {"w": breite, "type": "dxa"}) + rand)
               for breite in breiten]
    zellen = [element("tc", inhalt=spalte + text(werte, stil, wert, stelle))
              for spalte, (stil, wert) in zip(cycle(spalten), paare)]
    zeilen = ["".join(reihe) for reihe in batched(zellen, len(spalten))]
    if eigen.get("kopfwiederholen") == "ja":
        zeilen[0] = element("trPr", inhalt=element("tblHeader")) + zeilen[0]
    raster = "".join(element("gridCol", {"w": breite}) for breite in breiten)
    return element("tbl", inhalt=_tabellenkopf(werte, objekt) + element("tblGrid", inhalt=raster)
                   + "".join(element("tr", inhalt=zeile) for zeile in zeilen))


def _zellen(werte, objekt, spalten):
    """Zellen aus inhalt, sonst Zeile 1 aus der Liste an kopf, je Glied an zeilen eine Zeile."""
    if f"{objekt}.inhalt" in werte:
        return werte.liste(f"{objekt}.inhalt")
    leer = [""] * (spalten - 1)
    return werte.liste(werte.wert(f"{objekt}.kopf")) + [
        zelle for zeile in werte.liste(werte.wert(f"{objekt}.zeilen")) for zelle in [zeile, *leer]]


def _tabellenkopf(werte, objekt):
    """w:tblPr mit Tabellenformat, wahlweise Lage am Satzspiegel, und festen Spaltenbreiten."""
    eigen, abstand = werte.eigenschaften(objekt), ACHTELZOLL * WORD["twip"]
    waagrecht = JC[eigen["tabellenausrichtung"]] if "tabellenausrichtung" in eigen else None
    schwebend = (element("tblpPr", {"leftFromText": abstand, "rightFromText": abstand,
                                    "horzAnchor": "margin", "tblpXSpec": waagrecht,
                                    "tblpYSpec": SEITE[eigen["lage"]]})
                 + element("tblOverlap", {"val": "never"}) if "lage" in eigen else "")
    return element("tblPr", inhalt=(
        schalter("tblStyle", stil_id(eigen["tabellenstil"])) + schwebend
        + element("tblW", {"w": 0, "type": "auto"}) + element("tblLayout", {"type": "fixed"})
        + element("tblLook", OPTIONEN)))


def _zellenrand(werte, objekt):
    schluessel = {SEITE[wort]: f"{objekt}.zellenrand{wort}" for wort in ("links", "rechts")}
    raender = "".join(element(seite, {"w": werte.mass(s, "twip"), "type": "dxa"})
                      for seite, s in schluessel.items() if s in werte)
    return element("tcMar", inhalt=raender) if raender else ""
