# P5-2 STOPP-Bericht

Status: blockiert

Blocker:
P5-2D corpus_ingest_real Integrationstest auf pair_001 ist fehlgeschlagen.

Fehler:
alignment_confidence below threshold: 0.076440 < 0.850000

Gemessene Werte:
- pair_id: pair_001
- alignment_confidence: 0.076440
- raw_start_s: 323.0
- raw_end_s: 1254.35
- final_duration_seconds: 931.35
- kept_seconds_sum: 931.35
- duration_diff_seconds: 0.0

Bewertung:
Die Dauer-Validierung ist grün, aber die Confidence ist klar unter der Pflichtgrenze von 0.85.

Wahrscheinliche Ursache:
Der aktuelle P5-2A-Algorithmus macht ein globales STFT-Envelope-Matching und behandelt final.mp4 als einen zusammenhängenden Ausschnitt aus raw_mixed_audio.mp4.
Bei echten Pair-Videos besteht final.mp4 wahrscheinlich aus mehreren Schnitten/Kept-Segmenten. Dafür reicht ein einzelner globaler Offset nicht aus.

Nicht erfüllt:
- P5-2D Marker-Test ist rot.
- P5-2E darf nicht gestartet werden.
- Es darf keine cut_selection_map.json für pair_001 akzeptiert werden.

Vorschlag:
P5-2A muss erweitert werden:
- final.mp4 in kleinere Fenster splitten, z.B. 5-15 Sekunden
- jedes Fenster einzeln gegen raw_mixed_audio.mp4 alignen
- monotone Raw-Zeitfolge erzwingen
- Fenster zu kept_segments mergen
- alignment_confidence aus robustem Median/Quantil der Fenster-Confidence berechnen
- erst danach P5-2D erneut laufen lassen
