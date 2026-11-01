"""Liest die Werte der Vorlage aus den TOML-Dateien in QUELLE."""
import re
import tomllib
from pathlib import Path

QUELLE = Path(__file__).resolve().parents[1] / "quelle"
MENUE = re.compile(r"\{oberflaeche\.([a-z0-9]+)\}")
EINHEITEN = {"cm": "cm", "pt": "pt", "Zeile": "Zeilen", "Zeilen": "Zeilen"}
MASS = re.compile(rf"(-?\d+(?:,\d+)?) ({'|'.join(EINHEITEN)})")
PUNKT = {"cm": 72 / 2.54, "pt": 1, "Zeilen": 1}  # Größe in Punkt, Zeilen bleiben Zeilen
# Einheiten von Word je Punkt, zeile je Zeile wie w:line bei lineRule auto
WORD = {"punkt": 1, "twip": 20, "halbpunkt": 2, "achtelpunkt": 8, "emu": 12700, "zeile": 240}


def als_zahl(text):
    return float(text.replace(",", "."))


def umrechnen(zahl, einheit, ziel):
    """Deutsche Zahl in einheit als ganze Zahl in ziel, gerundet wie Word."""
    return round(als_zahl(zahl) * PUNKT[einheit] * WORD[ziel])


def wert_und_einheit(roh):
    """Zahlen und Einheit, wenn roh nur aus Maßen einer Einheit besteht, sonst roh ohne Einheit."""
    treffer = [MASS.fullmatch(glied) for glied in roh.split("; ")]
    einheiten = {EINHEITEN[t[2]] if t else None for t in treffer}
    if len(einheiten) > 1 or None in einheiten:
        return roh, ""
    return "; ".join(t[1] for t in treffer), einheiten.pop()


def dateien(quelle):
    """Inhalt der TOML-Dateien in quelle je Dateiname."""
    return {pfad.name: tomllib.loads(pfad.read_text(encoding="utf-8"))
            for pfad in sorted(Path(quelle).glob("*.toml"))}


def lese(inhalte):
    """Wert und Einheit je Schlüssel ohne [bestand]."""
    blaetter = ((f"{bereich}.{objekt}.{eigenschaft}", roh) for inhalt in inhalte.values()
                for bereich, objekte in inhalt.items() if bereich != "bestand"
                for objekt, eigenschaften in objekte.items()
                for eigenschaft, roh in eigenschaften.items())
    werte = {}
    for schluessel, roh in blaetter:
        wert, einheit = wert_und_einheit(roh)
        werte[schluessel] = {"wert": wert, "einheit": einheit}
    return werte


def menues(werte, sprache):
    """Setzt {oberflaeche.X} in der Sprache der Menüs ein."""
    for eintrag in werte.values():
        eintrag["wert"] = MENUE.sub(
            lambda treffer: werte[f"oberflaeche.{treffer[1]}.{sprache}"]["wert"], eintrag["wert"])


class Werte:
    """Werte aus quelle je Schlüssel, darüber das preset.

    Ein Schlüssel im Preset, den quelle nicht kennt, bricht ab. Einer Formatvorlage gibt ein
    Preset auch jede Eigenschaft, die eine andere trägt. Leere Werte eines Presets gelten nicht.
    Mit logos zeigen die Bilder ihr Logo statt des Platzhalters.
    """

    def __init__(self, quelle=QUELLE, sprache=None, preset=None, logos=False):
        self.quelle, self.logos = Path(quelle), logos
        inhalte = dateien(quelle)
        self.werte = lese(inhalte)
        if preset:
            namen, eigenschaften = zip(*(s.split(".")[1:] for s in self.werte
                                         if s.startswith("stil.")))
            bekannt = self.werte.keys() | {f"stil.{name}.{eigenschaft}" for name in set(namen)
                                           for eigenschaft in set(eigenschaften)}
            eigene = lese({preset.name: tomllib.loads(preset.read_text(encoding="utf-8"))})
            if fremd := eigene.keys() - bekannt:
                raise ValueError(f"unbekannte Schlüssel in {preset}: {', '.join(sorted(fremd))}")
            self.werte |= {s: eintrag for s, eintrag in eigene.items() if eintrag["wert"]}
        if sprache:
            menues(self.werte, sprache)
        self._bestand = {name: reihen for inhalt in inhalte.values()
                         for name, reihen in inhalt.get("bestand", {}).items()}

    def __contains__(self, s):
        return s in self.werte

    def wert(self, s):
        return self.werte[s]["wert"]

    def zahl(self, s):
        return als_zahl(self.wert(s))

    def ja(self, s):
        return self.wert(s) == "ja"

    def nach(self, s, tabelle):
        return tabelle[self.wert(s)]

    def liste(self, s):
        return self.wert(s).split("; ") if self.wert(s) else []

    def paare(self, *schluessel):
        """Glieder gleicher Stelle aus den Listen, ungleich lange brechen ab."""
        return list(zip(*map(self.liste, schluessel), strict=True))

    def masse(self, s, ziel):
        return [umrechnen(zahl, self.werte[s]["einheit"], ziel) for zahl in self.liste(s)]

    def mass(self, s, ziel):
        return self.masse(s, ziel)[0]

    def eigenschaften(self, objekt):
        return {s.rpartition(".")[2]: eintrag["wert"] for s, eintrag in self.werte.items()
                if s.rpartition(".")[0] == objekt}

    def objekte(self, bereich, eigenschaft):
        """Objekte des Bereichs, die eigenschaft tragen."""
        teile = (s.split(".") for s in self.werte)
        return [teil[1] for teil in teile if teil[0] == bereich and teil[2] == eigenschaft]

    def bestand(self, name):
        return [{"kennung": kennung, **felder} for kennung, felder in self._bestand[name].items()]
