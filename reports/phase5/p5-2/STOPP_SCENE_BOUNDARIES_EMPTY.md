# P5-2 STOPP-Bericht: Scene-Boundaries fehlen im echten Corpus

Status: blockiert

Kontext:
P5-2 wurde strategisch von Audio-Alignment auf Final-Scene-Inventar umgestellt.
Daf?r braucht jedes pair_NNN eine style_fingerprint.json mit scene_changes.boundaries_seconds.

Befund:
- pair_002: OK, boundaries=148
- pair_003: OK, boundaries=21
- pair_004: OK, boundaries=195
- pair_005: OK, boundaries=54
- pair_006: OK, boundaries=49
- pair_007: OK, boundaries=90
- pair_001: BLOCKIERT - boundaries_seconds leer, count=0

Bewertung:
P5-2A-Code ist auf mapping_version=2/final_scene_inventory umgestellt.
P5-2C Smoke-Tests sind lokal gr?n.
Der echte Real-Marker kann aber keine Cut-Map erzeugen, solange echte Scene-Boundaries fehlen.

Nicht erf?llt:
- keine 7 validen cut_selection_map.json
- P5-2E darf nicht gestartet werden
- keine Fake-Boundaries erzeugen

N?chster notwendiger Schritt:
P5-1 Scene-Change-Fingerprint muss echte boundaries_seconds f?r alle 7 Pair-Finals nachliefern.
Danach P5-2 Real-Marker erneut ausf?hren.
