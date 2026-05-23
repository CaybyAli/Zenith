# P5-2 STOPP-Bericht: Chroma-Matching-Versuch fehlgeschlagen

Status: blockiert

Kontext:
Nach Master-Freigabe wurde der Alignment-Kern testweise von Cross-Correlation auf Chroma-Feature-Matching umgestellt.

Ausgeführt:
- librosa lokal installiert
- Audio temporär via ffmpeg als 16000 Hz mono WAV extrahiert
- chroma_stft Features berechnet
- 10s Fenster / 8s Stride verwendet
- monotone Raw-Zeitfolge erzwungen
- Gesamt-Confidence als Median der Fenster-Confidences berechnet

Smoke-Beweis:
tests/test_learning_corpus_cut_selection_smoke.py
5 passed in 14.89s

Blocker:
Der echte corpus_ingest_real Marker-Test auf pair_001 ist weiterhin fehlgeschlagen.

Gemessener Fehler:
alignment_confidence below threshold: 0.608589 < 0.850000

Bewertung:
Chroma-Matching verbessert die Confidence deutlich gegenüber den vorherigen Versuchen, erreicht aber die Pflichtgrenze von 0.85 nicht.

Vergleich:
- Globaler STFT-Ansatz: 0.076440
- Windowed-STFT-Ansatz: 0.044804
- Chroma-Feature-Ansatz: 0.608589
- Pflichtgrenze: 0.850000

Nicht erfüllt:
- P5-2D bleibt rot
- P5-2E darf nicht gestartet werden
- Es darf keine cut_selection_map.json für pair_001 akzeptiert werden
- Der Chroma-Code wird nicht committed

Nächster Vorschlag:
Vor weiterem Algorithmus-Code braucht es eine tiefere Diagnose:
1. Top-3 Fenster-Confidences und Raw-Positionen ausgeben
2. Prüfen ob raw_mixed_audio.mp4 durch amerge für Chroma ungeeignet ist
3. Testweise raw_mixed_audio_amix_stereo.mp4 erzeugen und Chroma erneut vergleichen
4. Alternativ VAD/Audio-Event-Alignment oder längere 20-30s Chroma-Fenster testen
5. Erst danach neuer Fix-Commit
