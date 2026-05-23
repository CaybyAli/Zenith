# P5-2 STOPP-Bericht: DTW-Smoke fehlgeschlagen

Status: blockiert

Kontext:
Master hat DTW-basiertes Alignment freigegeben, um Greedy-Kollaps zu verhindern.

Ergebnis:
Der DTW-Versuch ist bereits im Smoke-Test fehlgeschlagen.

Fehler 1:
test_cut_selection_alignment_smoke
raw_start_s wurde als 0.0 erkannt, erwartet war ca. 2.0.

Fehler 2:
test_cut_selection_build_map_smoke
kept seconds outside tolerance:
kept=8.304
final=6.000
diff=2.304
tolerance=1.000

Bewertung:
Der einfache Full-Sequence-DTW-Pfad ist für diesen Use Case nicht korrekt.
Er zwingt final und raw zu stark auf einen Gesamtpfad und erkennt den finalen Ausschnitt im Raw nicht zuverlässig als Subsequence.

Nicht erfüllt:
- Smoke-Tests rot
- P5-2A darf nicht committed werden
- P5-2E darf nicht gestartet werden
- keine cut_selection_map.json akzeptieren

Nächster notwendiger Fix:
Der Algorithmus braucht Subsequence-DTW oder ein Seed-and-Track-Verfahren:
1. Startposition per MFCC-Subsequence-Suche finden
2. Danach lokal begrenzten DTW-Pfad berechnen
3. Pfad muss kept_seconds ≈ final_duration_seconds ergeben
4. Erst dann pair_001 erneut testen
