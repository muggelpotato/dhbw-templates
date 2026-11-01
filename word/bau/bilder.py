"""Bilder der Vorlage als DrawingML: Logos zur Seite verankert, Platzhalter in Zeile."""
import hashlib
import re
import struct
import urllib.request
from pathlib import PurePosixPath
from xml.sax.saxutils import quoteattr

import steuer
from paket import ACHTELZOLL, DML, element, lauf
from spez import WORD, als_zahl

# Z-Folge wie in Word: das erste Bild auf dieser Ebene, jedes weitere einen Schritt darüber
ZFOLGE, SCHRITT = 251658240, 1024
UMBRUCH = {"vor dem Text": 0, "hinter dem Text": 1}
ZEILE = {"in Zeile": "inline"}  # ein Platzhalter steht nur in Zeile, sonst bricht der Bau ab
PNG = b"\x89PNG\r\n\x1a\n"
SOF = (0xC0, 0xC1, 0xC2)  # Marken der JPEG-Segmente mit Höhe und Breite
# Erweiterung, mit der Word zum Rasterbild ein SVG ablegt
SVG = ('<a:extLst><a:ext uri="{{96DAC541-7B7A-43D3-8B79-37D633B846F1}}"><asvg:svgBlip '
       'xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" r:embed="{}"/>'
       '</a:ext></a:extLst>')


def _datei(werte, objekt):
    """Objekt im Bereich datei zum Bild objekt: mit Logos sein Logo, sobald es einen Link hat."""
    logo = f"datei.{werte.wert(f'{objekt}.logo')}"
    if werte.logos and werte.wert(f"{logo}.link"):
        return logo
    return f"datei.{werte.wert(f'{objekt}.datei')}"


def _inhalt(werte, datei):
    """Endung und Inhalt je Datei zu datei, das Rasterbild zuerst.

    Die Datei steht nach name in QUELLE, ohne name oder ohne die Datei lädt der Bau vom link, eine
    pruefsumme gilt für beide. Ein SVG ist ein Platzhalter in der Farbe der Platzhalter. Das PNG
    gleichen Namens braucht Word nur bis zum Speichern, dann rechnet es das PNG aus dem SVG neu.
    """
    eigen = werte.eigenschaften(datei)
    pfad = werte.quelle / "bilder" / eigen.get("name", "")
    if pfad.is_file():
        daten = pfad.read_bytes()
    else:
        with urllib.request.urlopen(eigen["link"]) as antwort:
            pfad, daten = PurePosixPath(eigen["link"]), antwort.read()
    if "pruefsumme" in eigen and hashlib.sha256(daten).hexdigest() != eigen["pruefsumme"]:
        raise ValueError(f"{pfad.name} passt nicht zu {datei}.pruefsumme")
    if pfad.suffix != ".svg":
        return [(pfad.suffix, daten)]
    farbe = werte.wert(f"stil.{werte.wert('dokument.rolle.platzhalter')}.farbe").lower()
    svg = daten.replace(re.search(rb'"#[0-9a-f]{6}"', daten)[0], f'"#{farbe}"'.encode())
    return [(".png", pfad.with_suffix(".png").read_bytes()), (".svg", svg)]


def _einbetten(werte, docx, datei, objekt):
    """Nimmt das Bild datei ins Paket, gibt Nummer, Rahmen, Bezüge und das Rasterbild."""
    dateien = _inhalt(werte, datei)
    nr = docx.nummer("image")
    bezuege = [docx.teil(f"word/media/image{nr + i}{endung}", daten, "image")
               for i, (endung, daten) in enumerate(dateien)]
    return nr, f'id="{steuer.kennzahl(nr, objekt)}" name="Picture {nr}"', bezuege, dateien[0][1]


def _zuschnitt(werte, datei):
    """Anteile links, oben, rechts und unten nach datei.zuschnitt in Prozent, sonst null."""
    s = f"{datei}.zuschnitt"
    prozente = werte.liste(s) if s in werte else []
    return [als_zahl(prozent) / 100 for prozent in prozente] or [0] * 4


def _bildpunkte(daten):
    """Breite und Höhe eines PNG oder JPEG in Bildpunkten."""
    if daten.startswith(PNG):
        return struct.unpack(">II", daten[16:24])
    stelle = 2
    while daten[stelle + 1] not in SOF:
        stelle += 2 + struct.unpack(">H", daten[stelle + 2:stelle + 4])[0]
    hoehe, breite = struct.unpack(">HH", daten[stelle + 5:stelle + 9])
    return breite, hoehe


def _einpassen(daten, zuschnitt, feld):
    """Lage und Größe des Bilds samt zuschnitt mittig im feld, so groß es unverzerrt passt."""
    links, oben, breite, hoehe = feld
    pixel_breite, pixel_hoehe = _bildpunkte(daten)
    weg_links, weg_oben, weg_rechts, weg_unten = zuschnitt
    verhaeltnis = (pixel_breite * (1 - weg_links - weg_rechts)
                   / (pixel_hoehe * (1 - weg_oben - weg_unten)))
    b, h = min(breite, round(hoehe * verhaeltnis)), min(hoehe, round(breite / verhaeltnis))
    return links + (breite - b) // 2, oben + (hoehe - h) // 2, b, h


def _grafik(bezuege, rahmen, groesse, zuschnitt=(0, 0, 0, 0)):
    """wp:docPr bis a:graphic zu den bezuege, Rasterbild und wahlweise SVG, mit zuschnitt."""
    raender = " ".join(f'{seite}="{round(anteil * 100000)}"'
                       for seite, anteil in zip("ltrb", zuschnitt) if anteil)
    quelle = f"<a:srcRect {raender}/>" if raender else ""
    blip = f'<a:blip r:embed="{bezuege[0]}"'
    blip += f">{SVG.format(bezuege[1])}</a:blip>" if len(bezuege) > 1 else "/>"
    return (f'<wp:docPr {rahmen}/><wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/>'
            f'</wp:cNvGraphicFramePr><a:graphic><a:graphicData uri="{DML}picture"><pic:pic>'
            f'<pic:nvPicPr><pic:cNvPr {rahmen}/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill>'
            f'{blip}{quelle}<a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
            f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext {groesse}/></a:xfrm>'
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData>'
            '</a:graphic>')


def bild(werte, docx, objekt):
    """Lauf mit dem Bild objekt, unverzerrt im Feld, zur Seite verankert und gesperrt."""
    datei = _datei(werte, objekt)
    nr, rahmen, bezuege, raster = _einbetten(werte, docx, datei, objekt)
    zuschnitt = _zuschnitt(werte, datei)
    feld = [werte.mass(f"{objekt}.{s}", "emu") for s in ("links", "oben", "breite", "hoehe")]
    links, oben, breite, hoehe = _einpassen(raster, zuschnitt, feld)
    if werte.ja(f"{objekt}.alternativtext"):
        rahmen += f" descr={quoteattr(werte.wert(f'text.{objekt}'))}"
    abstand, groesse = ACHTELZOLL * WORD["emu"], f'cx="{breite}" cy="{hoehe}"'
    anker = (
        f'<wp:anchor distT="0" distB="0" distL="{abstand}" distR="{abstand}" simplePos="0" '
        f'relativeHeight="{ZFOLGE + SCHRITT * (nr - 1)}" '
        f'behindDoc="{werte.nach(f"{objekt}.umbruch", UMBRUCH)}" locked="1" layoutInCell="1" '
        'allowOverlap="1"><wp:simplePos x="0" y="0"/>'
        f'<wp:positionH relativeFrom="page"><wp:posOffset>{links}</wp:posOffset></wp:positionH>'
        f'<wp:positionV relativeFrom="page"><wp:posOffset>{oben}</wp:posOffset></wp:positionV>'
        f'<wp:extent {groesse}/><wp:effectExtent l="0" t="0" r="0" b="0"/><wp:wrapNone/>'
        f'{_grafik(bezuege, rahmen, groesse, zuschnitt)}</wp:anchor>')
    return lauf(inhalt=element("drawing", inhalt=anker), merkmal=element("noProof"))


def zeilenbild(werte, docx, objekt):
    """Lauf mit dem Bild nach objekt.datei in Zeile, unverzerrt im Feld aus breite und hoehe."""
    datei = f"datei.{werte.wert(f'{objekt}.datei')}"
    _, rahmen, bezuege, raster = _einbetten(werte, docx, datei, objekt)
    feld = [0, 0, *(werte.mass(f"{objekt}.{s}", "emu") for s in ("breite", "hoehe"))]
    _, _, breite, hoehe = _einpassen(raster, (0, 0, 0, 0), feld)
    groesse, zeile = f'cx="{breite}" cy="{hoehe}"', werte.nach(f"{objekt}.umbruch", ZEILE)
    return lauf(inhalt=element("drawing", inhalt=(
        f'<wp:{zeile} distT="0" distB="0" distL="0" distR="0"><wp:extent {groesse}/>'
        f'<wp:effectExtent l="0" t="0" r="0" b="0"/>{_grafik(bezuege, rahmen, groesse)}'
        f'</wp:{zeile}>')))
