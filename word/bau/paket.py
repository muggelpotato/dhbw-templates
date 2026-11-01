"""Paket der Vorlage mit Kern, App und Einstellungen, dazu Grundlagen für XML im Namensraum w."""
import posixpath
import zipfile
from xml.sax.saxutils import escape, quoteattr

KOPF = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
OPC = "http://schemas.openxmlformats.org/package/2006/"
OFFICE = "http://schemas.openxmlformats.org/officeDocument/2006/"
W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
MSWORD = "http://schemas.microsoft.com/office/word"
DML = "http://schemas.openxmlformats.org/drawingml/2006/"
TYP = "application/vnd.openxmlformats-"
WML = TYP + "officedocument.wordprocessingml."
DOKUMENT = "word/document.xml"
# Inhaltstyp je Endung, ein Default für jede Endung im Paket
STANDARD = {"rels": TYP + "package.relationships+xml", "xml": "application/xml",
            "jpg": "image/jpeg", "png": "image/png", "svg": "image/svg+xml"}
BEZUG = OFFICE + "relationships/"
# Inhaltstyp und Beziehungstyp je Art eines Teils, ohne Inhaltstyp gilt der Default der Endung
ART = {
    "document": (WML + "document.main+xml", BEZUG + "officeDocument"),
    "settings": (WML + "settings+xml", BEZUG + "settings"),
    "styles": (WML + "styles+xml", BEZUG + "styles"),
    "numbering": (WML + "numbering+xml", BEZUG + "numbering"),
    "theme": (TYP + "officedocument.theme+xml", BEZUG + "theme"),
    "core": (TYP + "package.core-properties+xml", OPC + "relationships/metadata/core-properties"),
    "app": (TYP + "officedocument.extended-properties+xml", BEZUG + "extended-properties"),
    "header": (WML + "header+xml", BEZUG + "header"),
    "footer": (WML + "footer+xml", BEZUG + "footer"),
    "glossary": (WML + "document.glossary+xml", BEZUG + "glossaryDocument"),
    "customXml": (None, BEZUG + "customXml"),
    "customXmlProps": (TYP + "officedocument.customXmlProperties+xml", BEZUG + "customXmlProps"),
    "image": (None, BEZUG + "image"),
}
# Namensräume in document, hdr, ftr und glossaryDocument; Word schreibt beim Speichern eigene
NAMENSRAEUME = {"w": W, "r": OFFICE + "relationships", "wp": DML + "wordprocessingDrawing",
                "a": DML + "main", "pic": DML + "picture", "w14": MSWORD + "/2010/wordml",
                "w15": MSWORD + "/2012/wordml", "mc": MC}
ACHTELZOLL = 9  # Words Abstand schwebender Objekte zum Text links und rechts, in Punkt
KERN = {"dc:creator": "datei.dotx.autor", "cp:lastModifiedBy": "datei.dotx.zuletztvon"}
APP = {"Company": "datei.dotx.firma"}
# übrige compatSetting wie in jedem neuen Dokument ab Word 2013
KOMPATIBEL = {"overrideTableStyleFontSizeAndJustification": 1, "enableOpenTypeFeatures": 1,
              "doNotFlipMirrorIndents": 1, "differentiateMultirowTableHeaders": 1,
              "useWord2013TrackBottomHyphenation": 0}


def element(name, attribute=None, inhalt=""):
    """Element im Namensraum w ohne die Attribute None, ohne Inhalt leer geschlossen."""
    kopf = name + "".join(f" w:{attribut}={quoteattr(str(wert))}"
                          for attribut, wert in (attribute or {}).items() if wert is not None)
    return f"<w:{kopf}>{inhalt}</w:{name}>" if inhalt else f"<w:{kopf}/>"


def schalter(name, wert):
    """Element ohne w:val bei True, keins bei False, 0 und leer, sonst mit w:val."""
    return element(name, {"val": None if wert is True else wert}) if wert else ""


def stil_id(kennung):
    """styleId wie Word: die Kennung ohne Zeichen außerhalb ASCII."""
    return "".join(zeichen for zeichen in kennung if zeichen.isascii())


def wurzel(name, inhalt):
    """Wurzel w:NAME mit NAMENSRAEUME, w14 und w15 darf ein älteres Word übergehen."""
    namensraeume = "".join(f' xmlns:{praefix}="{uri}"' for praefix, uri in NAMENSRAEUME.items())
    return f'<w:{name}{namensraeume} mc:Ignorable="w14 w15">{inhalt}</w:{name}>'


def zeichenformat(stil, merkmal=""):
    """w:rPr mit rStyle, dahinter merkmal wie w:b, ohne beide nichts."""
    inhalt = schalter("rStyle", stil_id(stil)) + merkmal
    return f"<w:rPr>{inhalt}</w:rPr>" if inhalt else ""


def lauf(text="", stil="", inhalt="", merkmal=""):
    inhalt = inhalt or f'<w:t xml:space="preserve">{escape(text)}</w:t>'
    return f"<w:r>{zeichenformat(stil, merkmal)}{inhalt}</w:r>"


class Paket:
    """Teile mit Inhaltstyp und Beziehung, geschrieben als Zip in fester Folge."""

    def __init__(self):
        self.teile = {}

    def teil(self, name, inhalt, art, von=DOKUMENT):
        """Nimmt den Teil auf, Quelle der Beziehung ist von, leer das Paket; gibt ihre Kennung."""
        kennung = f"rId{1 + sum(quelle == von for _, _, quelle, _ in self.teile.values())}"
        self.teile[name] = inhalt, art, von, kennung
        return kennung

    def nummer(self, art):
        """Nächste Nummer eines Teils der Art, wie Word header1, image2 oder item1 zählt."""
        return 1 + sum(eintrag[1] == art for eintrag in self.teile.values())

    def schreibe(self, pfad):
        """Zip aus Inhaltstypen, Beziehungen und Teilen in der Folge der Aufnahme."""
        dateien = self._beziehungen() | {name: inhalt for name, (inhalt, *_) in self.teile.items()}
        with zipfile.ZipFile(pfad, "w") as archiv:
            for name, inhalt in {"[Content_Types].xml": self._typen(dateien), **dateien}.items():
                daten = inhalt if isinstance(inhalt, bytes) else KOPF + inhalt
                # ZipInfo ohne Zeit trägt wie Word den 1.1.1980, so bleibt das Paket byte-gleich
                archiv.writestr(zipfile.ZipInfo(name), daten, zipfile.ZIP_DEFLATED)

    def _typen(self, dateien):
        """Default je Endung der Dateien, Override je Teil mit eigenem Inhaltstyp."""
        endungen = dict.fromkeys(name.rpartition(".")[2] for name in dateien)
        standard = "".join(f'<Default Extension="{endung}" ContentType="{STANDARD[endung]}"/>'
                           for endung in endungen)
        je_teil = "".join(f'<Override PartName="/{name}" ContentType="{ART[art][0]}"/>'
                          for name, (_, art, *_) in self.teile.items() if ART[art][0])
        return f'<Types xmlns="{OPC}content-types">{standard}{je_teil}</Types>'

    def _beziehungen(self):
        """Je Quelle ein Teil in _rels, die Ziele relativ zum Ordner der Quelle."""
        beziehungen = {}
        for name, (_, art, von, kennung) in self.teile.items():
            ordner, _, datei = von.rpartition("/")
            beziehungen.setdefault(f"{ordner}/_rels/{datei}.rels".lstrip("/"), []).append(
                f'<Relationship Id="{kennung}" Type="{ART[art][1]}" '
                f'Target="{posixpath.relpath(name, ordner or ".")}"/>')
        return {teil: f'<Relationships xmlns="{OPC}relationships">{"".join(eintraege)}'
                      "</Relationships>" for teil, eintraege in beziehungen.items()}


def xmlteil(docx, item, kennung, namensraum):
    """customXml/itemN.xml mit itemPropsN.xml zu kennung und namensraum, bezogen vom Dokument."""
    nummer = docx.nummer("customXml")
    name = f"customXml/item{nummer}.xml"
    docx.teil(name, item, "customXml")
    docx.teil(f"customXml/itemProps{nummer}.xml",
              f'<ds:datastoreItem ds:itemID="{kennung}" xmlns:ds="{OFFICE}customXml">'
              f'<ds:schemaRefs><ds:schemaRef ds:uri="{namensraum}"/></ds:schemaRefs>'
              "</ds:datastoreItem>", "customXmlProps", von=name)


def _elemente(werte, schluessel):
    return "".join(f"<{name}>{escape(werte.wert(s))}</{name}>" for name, s in schluessel.items())


def kern(werte):
    dc, cp = werte.liste("speicher.kern.namensraum")
    name = "cp:" + werte.wert("speicher.kern.wurzel")
    return f'<{name} xmlns:cp="{cp}" xmlns:dc="{dc}">{_elemente(werte, KERN)}</{name}>'


def app(werte):
    return f'<Properties xmlns="{OFFICE}extended-properties">{_elemente(werte, APP)}</Properties>'


def einstellungen(werte):
    ja = werte.ja
    modus = {"compatibilityMode": werte.wert("dokument.einstellung.kompatibilitaet")}
    kompatibel = "".join(f'<w:compatSetting w:name="{name}" w:uri="{MSWORD}" w:val="{wert}"/>'
                         for name, wert in (modus | KOMPATIBEL).items())
    kinder = (
        schalter("removePersonalInformation", ja("datei.dotx.persoenlichentfernen")),
        schalter("embedTrueTypeFonts", ja("dokument.einstellung.schrifteneinbetten")),
        schalter("trackRevisions", ja("datei.dotx.ueberarbeitungen")),
        schalter("defaultTabStop", werte.mass("dokument.einstellung.standardtab", "twip")),
        schalter("autoHyphenation", ja("dokument.silbentrennung.automatisch")),
        schalter("consecutiveHyphenLimit", int(werte.zahl("dokument.silbentrennung.folgen"))),
        schalter("hyphenationZone", werte.mass("dokument.silbentrennung.zone", "twip")),
        schalter("doNotHyphenateCaps", not ja("dokument.silbentrennung.versalien")),
        schalter("defaultTableStyle", stil_id(werte.wert("dokument.einstellung.standardtabelle"))),
        schalter("updateFields", ja("dokument.einstellung.felderaktualisieren")),
        f"<w:compat>{kompatibel}</w:compat>",
        schalter("themeFontLang", werte.wert("dokument.standard.sprache")),
        schalter("doNotAutoCompressPictures", not ja("dokument.einstellung.bilderkomprimieren")),
        "<w15:chartTrackingRefBased/>",
    )
    return (f'<w:settings xmlns:mc="{MC}" xmlns:w="{W}" xmlns:w15="{MSWORD}/2012/wordml" '
            f'mc:Ignorable="w15">{"".join(kinder)}</w:settings>')
