# P5-2 STOPP-Bericht: Stream-2-MFCC20 knapp unter Threshold

Status: blockiert

Kontext:
Master-Option A wurde getestet: raw.mp4 Stream 2 direkt + MFCC20.

Konfiguration:
- raw stream index: 2
- n_mfcc: 20
- sample_rate: 16000
- hop_length: 512
- window_s: 12
- stride_s: 8
- raw_step_s: 1

Ergebnis:
- windows: 115
- median: 0.842470
- mean: 0.837495
- min: 0.715933
- max: 0.920253
- p25: 0.802065
- p75: 0.870765
- required_threshold: 0.850000

Bewertung:
Der Ansatz ist der bisher beste realistische Kandidat, bleibt aber unter der Pflichtgrenze.
Threshold wurde nicht gesenkt. P5-2E darf nicht gestartet werden.

Bottom-5 Fenster:
- final=464.0s -> raw=308.5s confidence=0.715933
- final=808.0s -> raw=310.5s confidence=0.733209
- final=872.0s -> raw=309.5s confidence=0.746753
- final=352.0s -> raw=313.5s confidence=0.753557
- final=344.0s -> raw=308.5s confidence=0.757761

Top-5 Fenster:
- final=368.0s -> raw=308.5s confidence=0.908133
- final=848.0s -> raw=831.3s confidence=0.909856
- final=600.0s -> raw=618.0s confidence=0.913606
- final=208.0s -> raw=569.4s confidence=0.918474
- final=768.0s -> raw=704.3s confidence=0.920253

Nicht erf?llt:
- pair_001 bleibt unter 0.85
- corpus_ingest_real Marker-Test bleibt rot
- keine cut_selection_map.json akzeptieren
- kein P5-2E Start
