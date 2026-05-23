# P5-2 STOPP-Bericht: MFCC Stream2 erzeugt keine valide Cut-Map

Status: blockiert

Kontext:
Nach Master-Entscheidung wurde Threshold auf 0.80 gesenkt und MFCC20 + raw.mp4 Stream 2 getestet.

Ergebnis:
Der Confidence-Threshold ist nicht mehr der Hauptblocker.
Die Validierung scheitert jetzt an der Dauer-Konsistenz.

Fehler:
kept seconds outside tolerance:
kept=178.400
final=931.350
diff=752.950
tolerance=1.000

Bewertung:
Der MFCC20-Stream2-Ansatz findet einzelne gute Fenster, aber viele Final-Fenster matchen auf dieselben Raw-Bereiche.
Dadurch entsteht keine vollständige, nicht überlappende Raw-Cut-Map.

Nicht erfüllt:
- Σ kept_seconds ≈ final_duration_seconds ±1s
- pair_001 cut_selection_map.json darf nicht akzeptiert werden
- P5-2E darf nicht gestartet werden

Technische Ursache:
Das aktuelle Fenster-Matching ist similarity-basiert, aber nicht pfad-konsistent.
Es erlaubt, dass viele Final-Fenster auf gleiche oder sehr nahe Raw-Positionen matchen.
Nach dem Sortieren/Mergen bleiben nur 178.4s statt 931.35s übrig.

Nächster notwendiger Fix:
Der Algorithmus braucht eine Pfad-/Timeline-Konsistenz:
- Final-Fenster müssen in finaler Reihenfolge bleiben
- Raw-Matches dürfen nicht auf denselben Bereich kollabieren
- pro Fenster muss eine coverage von ca. stride_s zur kept-Dauer beitragen
- bei unsicherem Match muss ein STOPP entstehen, nicht ein Fake-Kept-Segment

Kein Commit des aktuellen Core-Codes.
