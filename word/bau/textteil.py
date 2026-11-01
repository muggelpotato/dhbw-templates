"""Textteil der Vorlage: Kapitel mit Überschriften, Mustern und Tipps nach QUELLE als XML."""
import re

import absatz
import bilder
import steuer
from paket import element, schalter, zeichenformat

# verborgene Absatzmarke mit specVanish, so zeigt Word das Formatvorlagentrennzeichen
TRENNZEICHEN = "<w:rPr><w:vanish/><w:specVanish/></w:rPr>"
TEXT = re.compile(r"\{(text\.[^{}]+)\}")
FUSSNOTE = re.compile(r"\{fussnote:(\d+)\}")
STRICH = re.compile(r"\{strich(?::(fussnote))?\}")
BILD = re.compile(r"(\{bild(?::(mitte|pfeil))?\})?(.*)")
RANDABSTAND = 1  # Words Vorgabe in pt zwischen Absatzrand und Text


def textteil(werte, docx):
    """Je Kapitel aus text.textteil.gliederung sein XML: jede Überschrift, darunter ihre Folge."""
    stile = werte.liste("dokument.rolle.ueberschrift")
    for kapitel in gliederung(werte.wert("text.textteil.gliederung")):
        yield "".join(absatz.text(werte, stile[ebene], titel, ())
                      + "".join(muster(werte, docx, eintrag, ()) for eintrag in folge)
                      for ebene, titel, folge in kapitel)


def gliederung(text):
    """Kapitel aus text, je Zeile die Ebene nach den Punkten der Nummer, Titel und Folge."""
    kapitel = []
    for zeile in text.splitlines():
        kopf, _, folge = zeile.partition(" | ")
        nummer, _, titel = kopf.partition(" ")
        if "." not in nummer:
            kapitel.append([])
        kapitel[-1].append((nummer.count("."), titel, folge.split("; ") if folge else []))
    return kapitel


def muster(werte, docx, eintrag, stelle):
    """Eintrag einer Folge als XML, muster.X ein Tipp im Absatz, steuerelement.X ein Feld."""
    if eintrag in MUSTER:
        return MUSTER[eintrag](werte, docx, stelle)
    bereich, _, name = eintrag.partition(".")
    return BAUART[bereich](werte, name)


def _abbildung(werte, docx, stelle):
    bild = steuer.bild(werte, "bild", bilder.zeilenbild(werte, docx, "steuerelement.bild"))
    return _beschriftet(werte, absatz.absatz(werte.wert("muster.abbildung.stil"), bild),
                        "abbildung", "text.beschriftung.abbildungsquelle", stelle)


def _tabelle(werte, docx, stelle):
    return _beschriftet(werte, absatz.tabelle(werte, "muster.tabelle", "", stelle),
                        "tabelle", "text.beschriftung.tabellenquelle", stelle)


def _beschriftet(werte, inhalt, art, quelle, stelle):
    """inhalt mit Beschriftung nach beschriftung.ART, mit Quelle diese hinter dem Trennzeichen."""
    s = f"beschriftung.{art}"
    stil, geteilt = werte.wert(f"{s}.stil"), werte.ja(f"{s}.quelle")
    xml = absatz.absatz(stil, absatz.laeufe(werte, f"text.{s}", stelle),
                        TRENNZEICHEN if geteilt else "")
    if geteilt:
        xml += absatz.text(werte, stil, quelle, stelle)
    return inhalt + xml if werte.wert(f"{s}.lage") == "unter" else xml + inhalt


def tippfeld(werte, name):
    """Steuerelement um die Absätze zu NAME und die Leerzeile vor dem nächsten Tipp."""
    return steuer.block(werte, name, "".join(
        _strichabsatz(werte, eintrag["laenge"]) if eintrag["stil"] == "strich"
        else _absatz(werte, eintrag) for eintrag in absaetze(werte, name)) + absatz.absatz())


def absaetze(werte, name):
    """Bauplan je Zeile aus steuerelement.NAME.platzhalter oder text.platzhalter.NAME, in Twips."""
    eigen = werte.eigenschaften(f"steuerelement.{name}")
    schluessel = eigen.get("platzhalter", f"text.platzhalter.{name}")
    objekt, plan = schluessel.rpartition(".")[2], []
    text = FUSSNOTE.sub(r"{strich:fussnote}\n\g<0>", _wortlaut(werte, schluessel), count=1)
    for zeile in FUSSNOTE.sub(r"{bild}{hoch:\1} ", text).split("\n"):
        if treffer := STRICH.fullmatch(zeile):
            laenge = werte.mass(f"muster.{treffer[1] or objekt}.strichlaenge", "twip")
            plan.append({"stil": "strich", "laenge": laenge})
            continue
        bild, art, rest = BILD.fullmatch(zeile).groups()
        stuecke = steuer.stuecke(rest)
        if any("{" in stueck["t"] for stueck in stuecke):
            raise ValueError(f"{schluessel}: unbekannter Einschub in „{zeile}“")
        stil = werte.wert("dokument.rolle.fussnote" if bild else "dokument.rolle.standard")
        einzug = werte.mass(f"muster.{objekt}.pfeileinzug", "twip") if art == "pfeil" else 0
        plan.append({"stil": stil, "stuecke": stuecke, "mitte": art == "mitte", "einzug": einzug})
    return plan


def _wortlaut(werte, schluessel):
    return TEXT.sub(lambda treffer: _wortlaut(werte, treffer[1]), werte.wert(schluessel))


def _absatz(werte, eintrag):
    stuecke, einzug = eintrag["stuecke"], eintrag["einzug"]
    eigenschaften = ((element("ind", {"left": einzug}) if einzug else "")
                     + schalter("jc", eintrag["mitte"] and "center")
                     + (zeichenformat(**steuer.laufformat(werte, stuecke[-1])) if stuecke else ""))
    return absatz.absatz(eintrag["stil"], steuer.platzhaltertext(werte, stuecke), eigenschaften)


def _strichabsatz(werte, laenge):
    s = "muster.fussnote.strich"
    (vor, nach), links = werte.masse(f"{s}abstand", "twip"), werte.mass(f"{s}ausgleich", "twip")
    rechts = links - laenge + werte.mass("seite.format.breite", "twip") - sum(
        werte.mass(f"seite.rand.{wort}", "twip") for wort in ("links", "rechts", "bundsteg"))
    rand = {"val": "single", "sz": werte.mass(f"{s}staerke", "achtelpunkt"), "space": RANDABSTAND,
            "color": werte.wert(f"stil.{werte.wert('dokument.rolle.platzhalter')}.farbe")}
    zeile = {"before": vor, "after": nach, "line": werte.mass(f"{s}hoehe", "twip"),
             "lineRule": "exact"}
    return absatz.absatz(werte.wert("dokument.rolle.fussnote"), eigenschaften="".join((
        element("pBdr", inhalt=element("bottom", rand)), element("spacing", zeile),
        element("ind", {"left": links, "right": rechts}),
        zeichenformat("", element("sz", {"val": werte.mass(f"{s}hoehe", "halbpunkt")})))))


MUSTER = {"muster.abbildung": _abbildung, "muster.tabelle": _tabelle}
BAUART = {"muster": lambda werte, name: absatz.absatz(inhalt=steuer.frei(werte, name)),
          "steuerelement": tippfeld}
