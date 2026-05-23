# P5-2 Diagnosebericht: MFCC-Alignment knapp unter Threshold

Status: blockiert

Kontext:
Nach gescheitertem Chroma-Versuch wurden weitere Diagnose-Läufe auf pair_001 durchgeführt.

Ergebnisse:

1. AMIX vs. raw_mixed_audio
- raw_mixed median: 0.7231
- amix median: 0.7232
Bewertung: AMIX löst das Problem nicht.

2. Einzelne Raw-Audio-Spuren gegen final.mp4
Beste Spur:
- raw.mp4 stream 2
- median: 0.7569
- mean: 0.7568
- max: 0.8232

Weitere Spuren:
- stream 0 median: 0.6254
- stream 1 median: 0.4843
- stream 3 median: 0.0000

Bewertung:
final.mp4 passt am stärksten zu raw.mp4 Stream 2.

3. Feature-Vergleich auf Stream 2
- chroma median: 0.7517
- mfcc20 median: 0.8355
- mel40 median: 0.9858, aber wahrscheinlich Fake-Confidence wegen unplausibler Raw-Positionen
- spectral contrast median: 0.9723, aber wahrscheinlich Fake-Confidence wegen Raw-Position-Clustering
- combo_mfcc_chroma median: 0.7894

Bewertung:
MFCC20 ist der beste realistische Feature-Kandidat.

4. MFCC20 Parameter-Suche
Beste Konfiguration:
- n_mfcc=20
- window=12s
- stride=8s
- raw_step=1s
- median=0.8425

Pflichtgrenze:
- 0.8500

Bewertung:
MFCC20 ist knapp unter der Pflichtgrenze, aber nicht ausreichend.
Kein Threshold-Senken. Kein P5-2E.

Nicht erfüllt:
- pair_001 bleibt unter 0.85
- corpus_ingest_real bleibt für P5-2D nicht akzeptabel
- keine cut_selection_map.json darf erzeugt/committed werden

Nächster Vorschlag:
Vor weiterem Fix braucht es eine neue Master-Entscheidung:
A) Threshold bewusst auf 0.84 senken, nur wenn Master akzeptiert, dass MFCC20 realistisch genug ist.
B) Algorithmus wechseln auf audiovisuelle Segment-Matching-Diagnose.
C) Nur manuelle/halbautomatische Cut-Map-Erstellung aus Schnittprogramm-Export akzeptieren.
D) MFCC20 mit zusätzlicher Plausibilitätsprüfung der Raw-Zeitpfade testen, aber weiterhin ohne Threshold-Senkung.
