"""Abschnitte mit Seite, Zählung und Wechsel, dazu ihre Teile für Kopf und Fuß, als XML."""
from absatz import ENDE, FELDENDE, absatz, text
from paket import element, schalter, wurzel
from stile import ZAHLART
from textteil import gliederung

# Teil und Typ des Verweises je Art, in Words Folge im w:sectPr
TEIL = {"kopf": ("header", "default"), "fuss": ("footer", "default"),
        "kopferste": ("header", "first"), "fusserste": ("footer", "first")}
WURZEL = {"header": "hdr", "footer": "ftr"}
BEGINN = {"neu": True, "fortlaufend": False}
# Words Vorgaben decimal und nextPage schreibt Word nicht
ZAEHLUNG = ZAHLART | {"arabisch": None}
WECHSEL = {"neue Seite": None, "fortlaufend": "continuous"}
RAND = {"oben": "top", "rechts": "right", "unten": "bottom", "links": "left",
        "kopfzeile": "header", "fusszeile": "footer", "bundsteg": "gutter"}


def folge(werte):
    weitere = len(gliederung(werte.wert("text.textteil.gliederung"))) - 1
    return ["vorspann", "kapitel1", *["kapitel"] * weitere, "nachspann"]


def _seite(werte, name):
    """w:pgSz nach seite.format, w:pgMar nach seite.rand und vorrangig seite.NAME, in Twips."""
    eigene = werte.eigenschaften(f"seite.{name}")
    raender = {attribut: werte.mass(f"seite.{name if wort in eigene else 'rand'}.{wort}", "twip")
               for wort, attribut in RAND.items()}
    groesse = {"w": werte.mass("seite.format.breite", "twip"),
               "h": werte.mass("seite.format.hoehe", "twip")}
    return element("pgSz", groesse) + element("pgMar", raender)


def _kopf_fuss(werte, docx, art, objekt):
    """Teil headerN oder footerN mit einem Absatz nach objekt, gibt die Kennung der Beziehung."""
    eigen = werte.eigenschaften(objekt)
    xml = text(werte, eigen["stil"], eigen["inhalt"], (objekt, objekt.partition(".")[0]),
               titelstil=eigen.get("titelstil", ""))
    return docx.teil(f"word/{art}{docx.nummer(art)}.xml", wurzel(WURZEL[art], xml), art)


def _zaehlung(werte, objekt):
    neu = werte.nach(f"{objekt}.beginn", BEGINN)
    attribute = {"fmt": werte.nach(f"{objekt}.zaehlung", ZAEHLUNG),
                 "start": int(werte.zahl(f"{objekt}.startwert")) if neu else None}
    return element("pgNumType", attribute) if set(attribute.values()) != {None} else ""


def abschnitt(werte, docx, name, erster):
    """w:sectPr des Abschnitts name, legt dabei seine Teile für Kopf und Fuß an."""
    objekt = f"abschnitt.{name}"
    ersteseite = werte.ja(f"{objekt}.ersteseite")
    verweise = ""
    for art, (teil, typ) in TEIL.items():
        if (ersteseite or typ != "first") and not werte.ja(f"{objekt}.{art}verknuepft"):
            bereich = art.removesuffix("erste")
            kennung = _kopf_fuss(werte, docx, teil, f"{bereich}.{werte.wert(f'{objekt}.{art}')}")
            verweise += f'<w:{teil}Reference w:type="{typ}" r:id="{kennung}"/>'
    wechsel = None if erster else werte.nach(f"{objekt}.wechsel", WECHSEL)
    return element("sectPr", inhalt=verweise + schalter("type", wechsel) + _seite(werte, name)
                   + _zaehlung(werte, objekt) + schalter("titlePg", ersteseite))


def schluss(werte, name, absaetze, sect, letzter):
    """Absätze des Abschnitts name mit seinem w:sectPr, im letzten Abschnitt im Körper dahinter.

    Den Wechsel trägt ein Endabsatz ohne Text, auch ein schließendes Feldende; im letzten
    Abschnitt nur mit endabsatz.
    """
    if letzter and absaetze and not werte.ja(f"abschnitt.{name}.endabsatz"):
        return absaetze + sect
    feldende = absaetze.endswith(FELDENDE)
    ende = absatz(inhalt=ENDE if feldende else "", eigenschaften="" if letzter else sect)
    return absaetze.removesuffix(FELDENDE) + ende + (sect if letzter else "")
