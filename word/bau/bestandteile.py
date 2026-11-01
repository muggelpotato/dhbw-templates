"""Teile der Vorlage aus abschnitt.X.inhalt: Titelblatt, Formulare und Verzeichnisse als XML."""
import absatz
import bilder
import steuer
import textteil


def _huelle(werte, objekt, xml):
    s = f"{objekt}.huelle"
    return steuer.huelle(werte, werte.wert(s), xml) if s in werte else xml


def _folge(werte, bereich, name):
    """Platz eines Objekts im Text, eine Tabelle steht vor dem Absatz, den ihr vor nennt."""
    vor = werte.eigenschaften(f"{bereich}.{name}").get("vor")
    return werte.zahl(f"{bereich}.{vor or name}.position"), vor is None


def _objekt(werte, docx, bereich, name):
    """Objekt des Titelblatts: mit vor eine Tabelle, sonst ein Absatz mit seinen bilder vorn."""
    objekt = f"{bereich}.{name}"
    eigen, stelle = werte.eigenschaften(objekt), (objekt, bereich)
    if "vor" in eigen:
        return absatz.tabelle(werte, objekt, eigen["stil"], stelle)
    namen = werte.liste(f"{objekt}.bilder") if "bilder" in eigen else []
    logos = "".join(bilder.bild(werte, docx, f"{bereich}.{bild}") for bild in namen)
    laeufe = absatz.laeufe(werte, eigen["inhalt"], stelle, eigen.get("zeichenstil", ""))
    return _huelle(werte, objekt, absatz.absatz(eigen["stil"], logos + laeufe))


def titelblatt(werte, docx, bereich):
    namen = werte.objekte(bereich, "inhalt")
    return "".join(_objekt(werte, docx, bereich, name)
                   for name in sorted(namen, key=lambda name: _folge(werte, bereich, name)))


def formular(werte, docx, objekt):
    """Je Paar aus stile und inhalt ein Absatz, bei Objekten mit spaltenbreiten eine Tabelle."""
    paare = werte.paare(f"{objekt}.stile", f"{objekt}.inhalt")
    return _huelle(werte, objekt, "".join(
        absatz.tabelle(werte, wert, stil, (objekt,)) if f"{wert}.spaltenbreiten" in werte
        else absatz.text(werte, stil, wert, (objekt,)) for stil, wert in paare))


def verzeichnis(werte, docx, objekt):
    """Überschrift text.OBJEKT, Einträge aus muster, mit feld das Feld, sonst die Tabelle."""
    eigen, stelle = werte.eigenschaften(objekt), (objekt,)
    titelstil = eigen.get("titelstil") or werte.wert("dokument.rolle.verzeichnistitel")
    namen = werte.liste(f"{objekt}.muster") if "muster" in eigen else []
    xml = absatz.text(werte, titelstil, f"text.{objekt}", stelle) + "".join(
        textteil.muster(werte, docx, name, stelle) for name in namen)
    if "feld" in eigen:
        return xml + absatz.verzeichnis(eigen["feld"], eigen.get("eintragsstil", ""))
    return xml + absatz.tabelle(werte, objekt, eigen["eintragsstil"], stelle)


# Bauart je Vorsilbe eines Objekts in abschnitt.X.inhalt
BAUART = {"titelblatt": titelblatt, "formular": formular, "verzeichnis": verzeichnis,
          "anhang": formular}


def teile(werte, docx, abschnitt):
    """Objekte aus abschnitt.ABSCHNITT.inhalt, jedes in seiner Bauart."""
    return "".join(BAUART[objekt.partition(".")[0]](werte, docx, objekt)
                   for objekt in werte.liste(f"abschnitt.{abschnitt}.inhalt"))
