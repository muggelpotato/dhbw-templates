"""Inhaltssteuerelemente mit Bindung an die Angaben, dazu XML-Teile und Glossar als XML."""
import re
import uuid
from xml.sax.saxutils import escape, quoteattr

from paket import OFFICE, element, lauf, schalter, wurzel, zeichenformat

# Wertebereiche aus SPEZ zu Word; Rich-Text ist Words Vorgabe ohne Element
ART = {"Nur-Text": "text", "Rich-Text": "", "Datum": "date", "Kombinationsfeld": "comboBox",
       "Dropdown": "dropDownList", "Bild": "picture"}
SPERRE = {"keine": None, "Löschen": "sdtLocked", "Bearbeiten": "contentLocked",
          "Löschen und Bearbeiten": "sdtContentLocked"}
SPEICHERFORM = {"Datum": "date", "Datum und Uhrzeit": "dateTime", "Text": "text"}
KAESTCHEN = ("2610", "2612", "MS Gothic")  # Words Vorgabe: Zeichen leer und angekreuzt, Schrift
# U+00A0 nach SPEZ zwischen Wort und Zahl oder römischer Zahl, hinter „S.“ und in „z. B.“
AM_WORT = re.compile(r"(?<=[^\W\d_]) (?=\d|[IVXLC]+\b)|(?<=[^\W\d_]\.) (?=\d)"
                     r"|(?<=\b[^\W\d_]\.) (?=[^\W\d_]\.)")
STUECK = re.compile(r"\{(hoch|fett|stichwort):([^{}]+)\}|([^{]+|\{)")
MERKMAL = {"hoch": element("vertAlign", {"val": "superscript"}), "fett": element("b")}
ROLLE = {"klick": "klickfolge", "stichwort": "stichwort"}
XPATHWURZEL = re.compile(r"/\w+:(\w+)")
BIB = OFFICE + "bibliography"
# Attribut von b:Sources und Element der Musterquelle je Schlüssel, in der Folge des Schemas
QUELLSTIL = {"SelectedStyle": "speicher.quellen.stildatei",
             "StyleName": "speicher.quellen.stilname", "Version": "speicher.quellen.stilversion"}
MUSTERQUELLE = {
    "b:Tag": "text.musterquelle.kennung", "b:SourceType": "text.musterquelle.gattung",
    "b:Author": "text.musterquelle.verfasser", "b:Title": "text.musterquelle.titel",
    "b:Year": "text.musterquelle.jahr", "b:Edition": "text.musterquelle.auflage",
    "b:City": "text.musterquelle.ort", "b:Publisher": "text.musterquelle.verlag",
    "b:LCID": "dokument.standard.sprache"}
# Kennung und Platzhalterabsatz der Steuerelemente je Bau, also je Objekt Werte; glossar leert ihn
STEUERELEMENTE = {}


def kennung(*teile):
    return uuid.uuid5(uuid.NAMESPACE_URL, "/".join(map(str, teile)))


def kennzahl(*teile):
    """Feste Zahl zu den Teilen, positiv unter 2^31 wie Words w:id und wp:docPr id."""
    return kennung(*teile).int & 0x7FFFFFFF


def stuecke(text):
    """Stücke mit t und art: klick zwischen Backticks, hoch, fett und stichwort aus {ART:X}.

    U+00A0 nach SPEZ, in Klickfolgen vor jedem Pfeil.
    """
    return [{"t": t + wortlaut, "art": art or ("klick" if nr % 2 else "")}
            for nr, teil in enumerate(text.split("`"))
            for art, t, wortlaut in STUECK.findall(
                teil.replace(" →", "\u00a0→") if nr % 2 else AM_WORT.sub("\u00a0", teil))]


def laufformat(werte, stueck):
    """Zeichenstil und Merkmal eines Stücks als Schlüsselwörter für lauf und zeichenformat."""
    rolle = ROLLE.get(stueck["art"], "platzhalter")
    return dict(stil=werte.wert(f"dokument.rolle.{rolle}"), merkmal=MERKMAL.get(stueck["art"], ""))


def platzhaltertext(werte, stuecke):
    return "".join(lauf(stueck["t"], **laufformat(werte, stueck)) for stueck in stuecke)


def _steuerelement(werte, tag, objekt, platzhalter, *, typ="", inhalt="", bindung="",
                   zeichenstil="", zeigt="", als_block=False):
    """w:sdt nach steuerelement.OBJEKT, ohne inhalt mit dem platzhalter, mit als_block als Absatz.

    zeigt steht statt der Läufe des platzhalters, mit als_block als Absätze auch im Glossar.
    """
    eigen = werte.eigenschaften(f"steuerelement.{objekt}")
    texte, vorlaeufig = werte.eigenschaften("text.feldtitel"), eigen.get("entfernen") == "ja"
    titel = texte.get(objekt) or texte.get(tag) or (texte["voruebergehend"] if vorlaeufig else "")
    laeufe = zeigt or platzhaltertext(werte, stuecke(platzhalter))
    eintrag = laeufe if als_block and zeigt else platzhalter and element("p", inhalt=laeufe)
    liste, nummer = STEUERELEMENTE.setdefault(werte, []), kennung(eintrag)
    kopf = "".join((
        zeichenformat(zeichenstil), schalter("alias", titel), schalter("tag", tag),
        element("id", {"val": kennzahl(len(liste), tag)}),
        schalter("lock", SPERRE[eigen.get("sperre", "keine")]),
        eintrag and element("placeholder", inhalt=element("docPart", {"val": nummer.hex.upper()})),
        schalter("temporary", vorlaeufig), schalter("showingPlcHdr", not inhalt), bindung, typ))
    liste.append((nummer, eintrag))
    return element("sdt", inhalt=element("sdtPr", inhalt=kopf) + "<w:sdtEndPr/>"
                   + element("sdtContent", inhalt=inhalt or (eintrag if als_block else laeufe)))


def angabe(werte, name, stelle, zeichenstil="", *, eintraege=()):
    """Steuerelement an angabe.NAME nach der Gruppe der stelle, die Vorbelegung als Inhalt.

    Mit platzhaltereintrag der Gruppe zeigt eine Liste ihren ersten Anzeigetext als Platzhalter.
    """
    objekt, s = _gruppe(werte, stelle), f"angabe.{name}"
    gruppe = werte.eigenschaften(f"steuerelement.{objekt}")
    erster = eintraege and gruppe.get("platzhaltereintrag") == "ja"
    vorbelegung = werte.wert(f"{s}.vorbelegung")
    if vorbelegung and werte.wert(f"{s}.steuerelement") == "Dropdown" and (
            vorbelegung not in (erlaubt := werte.liste(f"text.auswahl.{name}"))):
        raise ValueError(f"{s}.vorbelegung: {vorbelegung}, erlaubt {' oder '.join(erlaubt)}")
    return _steuerelement(werte, name, objekt,
                          eintraege[0][0] if erster else werte.wert(f"text.platzhalter.{name}"),
                          typ=_typ(werte, f"{s}.steuerelement", eintraege),
                          inhalt=vorbelegung and lauf(vorbelegung, zeichenstil),
                          bindung=_bindung(werte, f"{s}.xpath"), zeichenstil=zeichenstil)


def auswahl(werte, schluessel, stelle):
    """Liste zu {text.OBJEKT.STELLE} mit den Werten aus text.auswahl.OBJEKT."""
    objekt = schluessel.split(".")[1]
    return angabe(werte, objekt, stelle,
                  eintraege=werte.paare(schluessel, f"text.auswahl.{objekt}"))


def frei(werte, name):
    """Steuerelement ohne Bindung nach steuerelement.NAME."""
    return _steuerelement(werte, name, name, werte.wert(f"text.platzhalter.{name}"),
                          typ=_typ(werte, f"steuerelement.{name}.art"))


def huelle(werte, name, absaetze):
    """Steuerelement nach steuerelement.NAME als Block um die Absätze, sie bleiben sichtbar."""
    return _steuerelement(werte, name, name, werte.wert(f"text.platzhalter.{name}"),
                          inhalt=absaetze, als_block=True)


def block(werte, name, absaetze):
    """Steuerelement nach steuerelement.NAME als Block, die absaetze sind sein Platzhalter."""
    return _steuerelement(werte, name, name, "", zeigt=absaetze, als_block=True)


def bild(werte, name, zeichnung):
    """Bild-Steuerelement nach steuerelement.NAME, die zeichnung zeigt es ohne Glossareintrag."""
    return _steuerelement(werte, name, name, "", typ=_typ(werte, f"steuerelement.{name}.art"),
                          zeigt=zeichnung)


def kaestchen(werte, name):
    """Leeres Kontrollkästchen nach steuerelement.NAME, dessen art Kontrollkästchen ist."""
    leer, an, schrift = KAESTCHEN
    typ = (f'<w14:checkbox><w14:checked w14:val="0"/><w14:checkedState w14:val="{an}" '
           f'w14:font="{schrift}"/><w14:uncheckedState w14:val="{leer}" w14:font="{schrift}"/>'
           "</w14:checkbox>")
    schriften = dict.fromkeys(("ascii", "eastAsia", "hAnsi"), schrift) | {"hint": "eastAsia"}
    return _steuerelement(werte, name, name, "",
                          typ=werte.nach(f"steuerelement.{name}.art", {"Kontrollkästchen": typ}),
                          inhalt=lauf(chr(int(leer, 16)), merkmal=element("rFonts", schriften)))


def angabenteil(werte):
    """Inhalt, Kennung und Namensraum des XML-Teils nach speicher.xmlteil, für paket.xmlteil."""
    teil = werte.eigenschaften("speicher.xmlteil")
    elemente = "".join(f"<{name}>{escape(wert)}</{name}>" if wert else f"<{name}/>"
                       for name, wert in _elemente(werte))
    return (f'<{teil["wurzel"]} xmlns="{teil["namensraum"]}">{elemente}</{teil["wurzel"]}>',
            teil["kennung"], teil["namensraum"])


def quellteil(werte):
    """Inhalt, Kennung und Namensraum des Teils der Quellenverwaltung, für paket.xmlteil."""
    felder = {name: escape(werte.wert(s)) for name, s in MUSTERQUELLE.items()}
    nachname, vorname = felder["b:Author"].split(", ")
    # Word schachtelt die Rolle b:Author in das Feld b:Author
    felder["b:Author"] = (f"<b:Author><b:NameList><b:Person><b:Last>{nachname}</b:Last>"
                          f"<b:First>{vorname}</b:First></b:Person></b:NameList></b:Author>")
    stil = "".join(f" {name}={quoteattr(werte.wert(s))}" for name, s in QUELLSTIL.items())
    quelle = "".join(f"<{name}>{wert}</{name}>" for name, wert in felder.items())
    return (f'<b:Sources xmlns:b="{BIB}" xmlns="{BIB}"{stil}><b:Source>{quelle}</b:Source>'
            "</b:Sources>", werte.wert("speicher.quellen.kennung"), BIB)


def glossar(werte):
    """Glossar mit einem Eintrag je Platzhaltertext in der Folge des ersten Auftretens.

    Nach File → New ordnet Word Kopf und Fuß dem ersten Eintrag zu, darum baut der Fuß zuerst.
    """
    eintraege = "".join(
        f'<w:docPart><w:docPartPr><w:name w:val="{nummer.hex.upper()}"/><w:category>'
        '<w:name w:val="General"/><w:gallery w:val="placeholder"/></w:category><w:types>'
        '<w:type w:val="bbPlcHdr"/></w:types><w:behaviors><w:behavior w:val="content"/>'
        f'</w:behaviors><w:guid w:val="{{{str(nummer).upper()}}}"/></w:docPartPr>'
        f"<w:docPartBody>{absatz}</w:docPartBody></w:docPart>"
        for nummer, absatz in dict(STEUERELEMENTE.pop(werte, [])).items() if absatz)
    return wurzel("glossaryDocument", f"<w:docParts>{eintraege}</w:docParts>")


def _typ(werte, s, eintraege=()):
    """Typelement zur Art an s, eine Liste ohne eintraege zeigt text.auswahl.NAME."""
    art, objekt = werte.nach(s, ART), s.rpartition(".")[0]
    if art in ("comboBox", "dropDownList"):
        wahl = werte.liste(f"text.auswahl.{s.split('.')[1]}")
        return element(art, {"lastValue": ""}, "".join(
            element("listItem", {"displayText": anzeige, "value": wert})
            for anzeige, wert in eintraege or zip(wahl, wahl)))
    if art == "date":
        return element(art, inhalt="".join((
            schalter("dateFormat", werte.wert(f"{objekt}.datumsformat")),
            schalter("lid", werte.wert(f"{objekt}.sprache")),
            schalter("storeMappedDataAs", werte.nach(f"{objekt}.speicherform", SPEICHERFORM)),
            schalter("calendar", "gregorian"))))
    return art and element(art)


def _gruppe(werte, stelle):
    """Gruppe zum genauesten Schlüssel der stelle, den ein steuerelement.GRUPPE.stellen nennt."""
    stellen = {s: name for name in werte.objekte("steuerelement", "stellen")
               for s in werte.liste(f"steuerelement.{name}.stellen")}
    return next(stellen[schluessel] for schluessel in stelle if schluessel in stellen)


def _bindung(werte, s):
    speicher = f"speicher.{_speicher(werte, s)}"
    praefixe = werte.paare(f"{speicher}.praefix", f"{speicher}.namensraum")
    return element("dataBinding", {
        "prefixMappings": " ".join(f"xmlns:{praefix}='{uri}'" for praefix, uri in praefixe),
        "xpath": werte.wert(s), "storeItemID": werte.wert(f"{speicher}.kennung")})


def _speicher(werte, s):
    """Speicher, in dessen Wurzel der XPath an s beginnt."""
    wurzeln = {werte.wert(f"speicher.{name}.wurzel"): name
               for name in werte.objekte("speicher", "wurzel")}
    return wurzeln[XPATHWURZEL.match(werte.wert(s))[1]]


def _elemente(werte):
    return [(name, werte.wert(f"angabe.{name}.vorbelegung"))
            for name in werte.objekte("angabe", "xpath")
            if _speicher(werte, f"angabe.{name}.xpath") == "xmlteil"]
