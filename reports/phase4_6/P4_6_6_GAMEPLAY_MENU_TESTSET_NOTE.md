# P4.6-6 Gameplay-vs-Menu Test-Set Note

## Status

Das im Originalauftrag geforderte manuell annotierte Test-Set `10 Clips x 30s` liegt im lokalen Repository nicht vor.

## Entscheidung

Die Sub-Phase wird nicht blockiert. Stattdessen werden fuer P4.6-6 verwendet:

- synthetische Modul-Tests fuer statische Menu-Frames vs. bewegte Gameplay-Frames
- ein realer `pair_001`-Smoke-Test fuer Timeline-Erzeugung und Score-Verteilung
- defensive Pipeline-Anbindung ohne harte Timeline-Strips, damit bestehende Phase-4.5-Stabilitaet nicht regressiert

## Offene Validierung

Die manuelle 90%-Accuracy-Akzeptanz bleibt offen, bis ein annotiertes Test-Set bereitliegt.
