"""Baut die Vorlage je Sprache der Menüs: das Paket in Python, den Abschluss in Word."""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import abschnitte
import bestandteile
import paket
import steuer
import stile
import textteil
from spez import QUELLE, Werte

BAU = Path(__file__).resolve().parent
ARBEIT = Path(tempfile.gettempdir()) / "dhbw-templates-bau"
ROH = "roh.docx"
GLOSSAR = "word/glossary/document.xml"


def parameter(argv=None):
    aufruf = argparse.ArgumentParser(description=__doc__)
    aufruf.add_argument("--preset", type=Path, metavar="DATEI",
                        help="eigene Werte über der Quelle, ihr Name hängt an der .dotx")
    aufruf.add_argument("--ohne-logos", action="store_true", help="Platzhalter statt Logos")
    return aufruf.parse_args(argv)


def _inhalte(werte, docx):
    """Inhalte der Abschnitte in Folge, gebaut erst beim Abruf."""
    yield bestandteile.teile(werte, docx, "vorspann")
    yield from textteil.textteil(werte, docx)
    yield bestandteile.teile(werte, docx, "nachspann")


def _koerper(werte, docx):
    """Inhalt von w:body, je Abschnitt Kopf und Fuß vor dem Inhalt, so folgt das Glossar Word."""
    folge, xml, inhalte = abschnitte.folge(werte), "", _inhalte(werte, docx)
    for nr, name in enumerate(folge):
        sect = abschnitte.abschnitt(werte, docx, name, nr == 0)
        xml += abschnitte.schluss(werte, name, next(inhalte), sect, nr == len(folge) - 1)
    return xml


def baue(werte, ordner):
    """Paket einer Sprache als ROH in ordner."""
    docx = paket.Paket()
    koerper = paket.element("body", inhalt=_koerper(werte, docx))
    docx.teil(paket.DOKUMENT, paket.wurzel("document", koerper), "document", von="")
    plan = stile.plan(werte)
    formate, listen = stile.formatvorlagen(werte, plan), stile.listen(werte, plan)
    docx.teil("word/styles.xml", formate, "styles")
    docx.teil("word/numbering.xml", listen, "numbering")
    docx.teil("word/theme/theme1.xml", stile.design(werte), "theme")
    docx.teil("word/settings.xml", paket.einstellungen(werte), "settings")
    docx.teil("docProps/core.xml", paket.kern(werte), "core", von="")
    docx.teil("docProps/app.xml", paket.app(werte), "app", von="")
    paket.xmlteil(docx, *steuer.angabenteil(werte))
    paket.xmlteil(docx, *steuer.quellteil(werte))
    docx.teil(GLOSSAR, steuer.glossar(werte), "glossary")
    docx.teil("word/glossary/styles.xml", formate, "styles", von=GLOSSAR)
    # ohne eigene Listen legt Word beim Speichern welche mit Zufallskennungen an
    docx.teil("word/glossary/numbering.xml", listen, "numbering", von=GLOSSAR)
    docx.schreibe(ordner / ROH)


def _word(ordner, dotx):
    """Abschluss in Word über word.ps1, gibt den Rückgabewert."""
    return subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                           BAU / "word.ps1", "-Eingabe", ordner / ROH,
                           "-Vorlage", ordner / dotx]).returncode


def main(argv=None):
    """Baut je Sprache der Menüs und legt die .dotx nach word, wenn keine Sprache scheitert."""
    wahl = parameter(argv)
    zusatz = f"-{wahl.preset.stem}" if wahl.preset else ""
    namen = Werte(preset=wahl.preset).paare("datei.dotx.menues", "datei.dotx.name")
    vorlagen = []
    for sprache, name in namen:
        ordner, dotx = ARBEIT / sprache, name.replace(".dotx", f"{zusatz}.dotx")
        shutil.rmtree(ordner, ignore_errors=True)
        ordner.mkdir(parents=True)
        baue(Werte(QUELLE, sprache, wahl.preset, not wahl.ohne_logos), ordner)
        if _word(ordner, dotx):
            return f"{sprache}: Abschluss in Word gescheitert"
        vorlagen.append(ordner / dotx)
    for dotx in vorlagen:
        print(shutil.copy(dotx, BAU.parent))


if __name__ == "__main__":
    sys.exit(main())
