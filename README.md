# Vorlagen für wissenschaftliches Arbeiten am SZI der DHBW Lörrach

Word-Vorlage mit Zitierstilen für Word und Zotero. Für Projekt-, Seminar-, Studien- und Bachelorarbeiten in Informatik und Wirtschaftsinformatik. Sie folgt den [Richtlinien für wissenschaftliche Arbeiten des SZI](https://dhbw-loerrach.de/fileadmin/studiengaenge/wi-application-management/WissArb/Richtlinien_wissenschaftliche_Arbeiten_SZI_3_1.pdf) (v3.1, 17.05.2020). Ehrenwörtliche Erklärung und Sperrvermerk stehen im Wortlaut der [StuPrO der DHBW](https://dhbw-loerrach.de/pruefungsamt/rund-um-das-studium/studien-und-pruefungsordnung) für Studienbeginn ab 01.10.2024

> [!Warning]
Inoffiziell, nicht von der DHBW herausgegeben oder geprüft. Ohne Gewähr, Richtlinie und Betreuer gehen vor

## Installieren

1. Bei deutscher UI in Word die [Vorlage für deutsche UI](https://github.com/muggelpotato/dhbw-templates/releases/latest/download/Wissenschaftliche-Arbeit-SZI-deutsch.zip) laden, bei englischer die [Vorlage für englische UI](https://github.com/muggelpotato/dhbw-templates/releases/latest/download/Wissenschaftliche-Arbeit-SZI-englisch.zip)
2. ZIP entpacken und `SZI-DHBW-Loerrach.xsl` nach `%APPDATA%\Microsoft\Bibliography\Style` (`Win+R`) kopieren
3. Word schließen und neu starten
4. Doppelklick auf die `.dotx` legt eine neue Arbeit an

## Zotero

1. In Zotero unter Edit → Settings → Cite mit `+` die Datei `SZI-DHBW-Loerrach.csl` aus der ZIP hinzufügen
2. In Word unter Zotero → Document Preferences `SZI DHBW Lörrach` wählen
3. Unter der Überschrift Quellenverzeichnis das Verzeichnis von Word löschen und dort Zotero → Add/Edit Bibliography klicken

## Selbstbau

Der Bau braucht Word, PowerShell 5.1 und Python ab 3.12:

- `python word\bau\bau.py` baut beide `.dotx` nach `word\`
- Um eigene Angaben/Konfigurationen vorzubelegen, `word\presets.toml` als `word\meine.toml` kopieren und befüllen.  
Dann `python word\bau\bau.py --preset word\meine.toml`
- Der Bau lädt das Logo der DHBW selbst und setzt es ein, das Firmenlogo vom Link in `word\meine.toml`. Ohne Internet das Logo vorher von Hand als `word\quelle\bilder\DHBW_LOE_Drucklogo.jpg` ablegen oder mit `--ohne-logos` bauen
