# P5-2 STOPP-Bericht: Windowed-Alignment-Upgrade fehlgeschlagen

Status: blockiert

Kontext:
Der Master hat das Algorithmus-Upgrade von globalem Single-Offset auf Windowed Alignment freigegeben.

Ausgeführt:
- final.mp4 wurde in 10s-Fenster mit 2s Overlap / 8s Stride gematcht
- monotone Raw-Zeitfolge wurde erzwungen
- Confidence wurde als Median der Fenster-Confidences berechnet
- Smoke-Tests blieben grün

Smoke-Beweis:
tests/test_learning_corpus_cut_selection_smoke.py
5 passed in 0.64s

Blocker:
Der echte corpus_ingest_real Marker-Test auf pair_001 ist weiterhin fehlgeschlagen.

Gemessener Fehler:
alignment_confidence below threshold: 0.044804 < 0.850000

Bewertung:
Das freigegebene Windowed-Alignment-Modell reicht für pair_001 noch nicht.
Die Confidence ist sogar niedriger als beim vorherigen globalen Ansatz.

Wahrscheinliche Ursache:
Das Audio im final.mp4 ist nicht zuverlässig als direkte 10s-Fenster gegen raw_mixed_audio.mp4 matchbar.
Mögliche Gründe:
- final.mp4 enthält starke Audio-Bearbeitung gegenüber raw_mixed_audio.mp4
- Tonspuren wurden beim raw_mixed_audio.amerge anders kanalisiert als im final
- Final-Audio ist durch Musik, Ducking, Gain, Filter oder Schnittübergänge verändert
- Reine STFT-Energie-Envelope ist zu schwach für echtes Edit-Alignment

Nicht erfüllt:
- P5-2D ist rot
- P5-2E darf nicht gestartet werden
- Es darf keine cut_selection_map.json für pair_001 akzeptiert werden

Nächster Vorschlag:
Vor dem nächsten Algorithmus-Fix muss zuerst eine Audio-Diagnose auf pair_001 laufen:
1. ffprobe raw_mixed_audio.mp4 und final.mp4: Audio codec, channels, sample_rate, duration
2. Testweise raw_mixed_audio mit amix/stereo statt amerge erzeugen und Alignment vergleichen
3. Zusätzlich MFCC-/Spectral-Fingerprint statt nur STFT-Energy testen
4. Erst danach neuer Algorithmus-Commit
