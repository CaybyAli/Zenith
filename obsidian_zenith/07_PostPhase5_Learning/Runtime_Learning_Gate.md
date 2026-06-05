# Runtime Learning Gate

Status: locked / later

## Zweck

Dieses Gate beschreibt den spaeteren echten Schlaf-/Learning-Run.

Der Run ist NICHT Teil des P5-L-Abschlusses.
Er ist ein spaeteres Runtime-Gate.

## Startbedingungen

Nur starten, wenn alle Punkte erfuellt sind:

- Master-GO vorhanden.
- Ali startet bewusst.
- Qwen lokal erreichbar.
- Enable-Flag gesetzt.
- Stop-Datei / Stop-Schalter vorhanden.
- Timeout / Max-Items vorhanden.
- Reports-Output definiert.
- Kein Render.
- Kein Ingest.
- Keine Musik.
- Kein Qwen-Autocut.
- Phase 5.5 nicht aktiv.

## Verhalten beim Schlaf-Run

Wenn Ali schlafen geht:
- Qwen darf nur analysieren.
- System darf nur kontrollierte Items bearbeiten.
- Keine Produktionsdateien ueberschreiben.
- Reports lokal erzeugen.
- Stop-Schalter beachten.

Wenn Ali aufwacht:
- Stop setzen oder kontrolliert beenden.
- Run macht sauberes Ende.
- Abschlussbericht schreiben:
  - wie viele Items analysiert.
  - welche Kategorien.
  - welche Risiken.
  - was vorgeschlagen.
  - was gespeichert.
  - was uebersprungen.
  - Owner Review noetig ja/nein.

## Harte Verbote

- Kein Autocut.
- Kein Render.
- Kein Ingest.
- Keine Musik.
- Keine Phase 5.5.
- Keine Timeline-Aenderung ohne eigenes Gate.
- Keine externen Netzwerke.
- Keine API-Keys.
