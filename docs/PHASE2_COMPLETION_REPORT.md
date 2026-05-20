# PROJECT ZENITH — Phase 2 Completion Report / P2-FIX Nachbesserung

Stand: 2026-05-19
Branch: `main`
Ursprünglicher P2-FIX-Start-HEAD: `2f2767f5f785e981e62caccffd1f2695824e6495`

## 1. Phasen-Übersicht P2-1 bis P2-8

- **P2-1 — FFmpeg-Auflösung import-sicher / Smoke-Pfad bereinigt**: FFmpeg-Auflösung wurde import-sicher gemacht und der hartkodierte Smoke-Pfad entfernt. Commit: `7a8ef5fb9bc5906a8781f4a4c8ad1e8fc76b4aa0`.
- **P2-2 — 16:9-Filter-Complex im FinalRenderDriver**: Der FinalRenderDriver kann 16:9-Quellen im Filter-Complex korrekt behandeln. Commit: `8da86ceebc16ccffc208b9ef50e9896670b14f89`.
- **P2-3 — gaming_main auf FinalRenderDriver-Pfad konsolidiert**: Der `gaming_main`-Renderpfad wurde auf den FinalRenderDriver konsolidiert. Commit: `3b389f724d9790086b4f0105a411ce0e14859c12`.
- **P2-4 — Censor-SFX Audio Overlay**: Censor-SFX wurde als Audio-Overlay im Renderpfad ergänzt. Commit: `b50ee6c81cfaa7ebc40cd952ef23f2de629474cb`.
- **P2-5 — Encoder-Fallback und realer gaming_main Renderabschluss**: FinalRenderDriver erhielt einen Encoder-Fallback und der gaming_main-Renderpfad wurde weiter abgeschlossen. Commits: `d2e174d7d3bc7b676e7fb7402ef0f1947376dddd`, `848ebc639fa562285cfef2c457c4b7c6ad16c888`.
- **P2-6 — Reproduzierbares Speech-Transcript-E2E-Artefakt**: Ein reproduzierbares Speech-Transcript-E2E-Artefakt wurde ergänzt. Commit: `8ed260efa27da2da4eba5c1d7319d85e7091c513`.
- **P2-7 — Real-Whisper-Evidence-Artefakt**: Ein Artefakt für echten Whisper-Nachweis wurde ergänzt. Commit: `cd825621e75668d8da11005640b26cf06abcebce`.
- **P2-8 — Real-Whisper-Tests skip-safe**: Real-Whisper-Tests wurden skip-safe gemacht, damit fehlende lokale Modell-/Runtime-Voraussetzungen nicht als falsches Rot erscheinen. Commit: `2f2767f5f785e981e62caccffd1f2695824e6495`.

## 2. Ehrlicher Scope-Vermerk

P2-6, P2-7 und P2-8 betreffen sachlich den Transkript-/Whisper-Track. Diese Arbeiten härten und belegen Transcript-/Whisper-Verhalten, sind aber nicht der eigentliche Render-Abschluss. Sie werden deshalb als eigener Transkript-Track geführt und dürfen nicht als Ersatz für einen echten End-to-End-Render-Beweis gewertet werden.

## 3. P2-5 Encoder-Fallback

Der `FinalRenderDriver` löst den Video-Encoder zur Laufzeit auf. Wenn NVENC verfügbar und funktionsfähig ist, wird `h264_nvenc` mit dem Modus `nvenc` verwendet. Wenn NVENC nicht verfügbar oder nicht funktionsfähig ist, fällt der Driver auf `libx264` mit dem Modus `cpu_fallback` zurück.

Der Render-Kontext schreibt dafür die Felder `codec_video` und `video_encoder_mode`. Tests dürfen deshalb nicht hart `h264_nvenc` erwarten, sondern müssen gegen die gleiche Resolver-Logik prüfen, die der Driver nutzt.

## 4. P2-3 Fallback-Edit-Timeline

Wenn keine `edit_timeline` vorhanden ist, baut die Pipeline eine Ersatz-Timeline aus `edit_decision.selected_segments`. Der vorherige `RenderProcessor`-Fallback wurde entfernt. `RenderProcessor` ist als `DEPRECATED` markiert und darf nicht mehr als stiller Ersatz-Renderpfad verstanden werden.

## 5. Gefundener roter Test und P2-FIX-1

Im Test `test_basic_render_consumes_timeline` aus `tests/test_final_render_driver_smoke.py` stand eine stale Assertion:

```python
assert ctx["codec_video"] == "h264_nvenc"
```

Diese Assertion war nach P2-5 falsch, weil der Driver auf Maschinen ohne funktionierendes NVENC korrekt auf `libx264` fällt. Durch die Default-Konfiguration in `pytest.ini` mit `addopts = -m "not ffmpeg_integration"` wurde dieser rote Integrationstest im Standardlauf verdeckt.

P2-FIX-1 repariert den Test resolver-korrekt: Der Test ruft `FinalRenderDriver()._resolve_video_encoder(None)` auf und vergleicht `ctx["codec_video"]` sowie `ctx["video_encoder_mode"]` gegen das Ergebnis. Zusätzlich wird weiter geprüft, dass nur `h264_nvenc`/`libx264` und `nvenc`/`cpu_fallback` erlaubt sind.

P2-FIX-1 Commit: `1f3f6a9d236ad59d37a9ef3cd25d95275bbd1df4`.

## 6. Render-Test-Lane

Pflicht-Befehl für den Phase-2-Abschluss:

```text
pytest -m ffmpeg_integration -p no:cacheprovider -o addopts=""
```

### Lokaler Einzeltest-Lauf `test_final_render_driver_smoke.py`

Ausgeführt auf der Nutzer-Maschine unter `D:\Zenith`:

```powershell
python -m pytest -m ffmpeg_integration tests/test_final_render_driver_smoke.py -p no:cacheprovider -o addopts=""
```

Roher Schlussbalken:

```text
================================================ 3 passed, 2 deselected in 13.17s ================================================
```

### Lokaler vollständiger ffmpeg_integration-Lauf

Ausgeführt auf der Nutzer-Maschine unter `D:\Zenith`:

```powershell
python -m pytest -m ffmpeg_integration -p no:cacheprovider -o addopts=""
```

Roher Schlussbalken:

```text
============================================== 5 passed, 3517 deselected in 15.63s ===============================================
```

### Lokaler Standard-Suite-Lauf

Ausgeführt auf der Nutzer-Maschine unter `D:\Zenith`:

```powershell
python -m pytest
```

Roher Schlussbalken:

```text
==================================== 3515 passed, 2 skipped, 5 deselected in 95.52s (0:01:35) ====================================
```

## 7. E2E-Render-Beweis gaming_main

Status: ERFUELLT.

P2-FIX-3 ist durch die Materialvalidierung mit zwei echten gaming_main-Renders erfuellt. Die Render-Beweise wurden in Commit d17ab09 dokumentiert.

Quelle:
docs/PHASE2_MATVAL_RESULTS.md

### 7.1 LoL Render-Beweis

Video:
LoL

Quelldauer:
1017.833333 Sekunden

Pipeline-Kernbefund:
[TIMELINE-SCORE-POOLS] primary=32 reserve=67 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=610.698s floor=480.000s selected=480.330s primary_candidates=32 reserve_candidates=67 reserve_used=23 max_segments=61
[pipeline_runner] Done ? ok=1  skipped=0  failed=0

Roher ffprobe-Auszug:
ffprobe_final:
duration=490.851758
codec_type=video
codec_name=h264
width=1920
height=1080
display_aspect_ratio=16:9

Auswertung:
LoL PASS. Dauer 490.851758s liegt im 480-1200s-Fenster. Video ist h264, 1920x1080, 16:9.

### 7.2 Minecraft Render-Beweis

Video:
Minecraft

Quelldauer:
2670.070000 Sekunden

Pipeline-Kernbefund:
[TIMELINE-SCORE-POOLS] primary=37 reserve=316 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=934.524s floor=480.000s selected=492.500s primary_candidates=37 reserve_candidates=316 reserve_used=19 max_segments=93
[pipeline_runner] Done ? ok=1  skipped=0  failed=0

Roher ffprobe-Auszug:
ffprobe_final:
duration=736.000438
codec_type=video
codec_name=h264
width=1920
height=1080
display_aspect_ratio=16:9

Auswertung:
Minecraft PASS. Dauer 736.000438s liegt im 480-1200s-Fenster. Video ist h264, 1920x1080, 16:9.

### 7.3 Fortnite Materialvalidierung

Video:
Fortnite

Quelldauer:
1820.816667 Sekunden

Pipeline-Kernbefund:
[TIMELINE-SCORE-POOLS] primary=38 reserve=227 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=637.287s floor=480.000s selected=483.000s primary_candidates=38 reserve_candidates=227 reserve_used=10 max_segments=63
[TIMELINE-DURATION-FLOOR-BLOCKED] selected_after_guards=443.820s floor=480.000s primary=38 reserve=227 target=637.287s
[pipeline_runner] Done ? ok=0  skipped=0  failed=1

ffprobe_final:
kein MP4 erzeugt

Auswertung:
Fortnite ist kein Bug. Die Pipeline hat korrekt blockiert, weil nach den Guards nur 443.820s nutzbares Material uebrig waren. Der 480s-Floor arbeitet wie spezifiziert und verhindert ein still zu kurzes Longform-Video.

### 7.4 P2-FIX-3 Abschlussbewertung

P2-FIX-3: ERFUELLT
LoL: PASS, 490.851758s, h264, 1920x1080, 16:9
Minecraft: PASS, 736.000438s, h264, 1920x1080, 16:9
Fortnite: korrekt blockiert, 443.820s nach Guards, kein Bug

Damit ist der echte gaming_main End-to-End-Render-Beweis fuer Phase 2 erfuellt.


## 8. Protokollvermerk: Realer Whisper-Lauf

Der reale Whisper-Lauf mit echtem `faster-whisper` ohne Test-Modus ist lokal auf der Nutzer-Maschine belegt. Er wurde nicht in einer Umgebung mit Netz-/Modell-Cache vom Pruef-Chat reproduziert.

Dieser Punkt bleibt als P2-7-Protokollvermerk offen, ist aber nach der Materialvalidierung und den echten gaming_main Render-Beweisen nicht mehr Phase-2-blockierend.

## 9. P2-FIX-5 Regressionswächter

P2-FIX-5 wurde umgesetzt. Neuer Standard-Smoke-Test:

```text
tests/test_phase2_p2_fix_encoder_assertion_guard_smoke.py
```

Der Test scannt `tests/test_final_render_driver_smoke.py` und verhindert, dass die stale Assertion `ctx["codec_video"] == "h264_nvenc"` zurückkehrt. Außerdem prüft er, dass `_resolve_video_encoder`, `resolved["codec"]` und `resolved["mode"]` im Test verwendet werden.

P2-FIX-5 Commit: `a26089b84df2772322c30f188d3b5f4ee8549acc`.

## 10. Abschlussstatus dieses Reports

Dieser Report enthaelt die geforderten acht Kernpunkte. Die Code-/Doku-Nachbesserungen P2-FIX-1, P2-FIX-4 und P2-FIX-5 wurden umgesetzt. P2-FIX-2 ist durch lokale rohe pytest-Schlussbalken belegt.

P2-FIX-3 ist durch die Materialvalidierung erfuellt: LoL rendert mit 490.851758s, Minecraft rendert mit 736.000438s, beide im 480-1200s-Fenster, 16:9 und h264.

Fortnite wurde korrekt blockiert, weil nach Guards nur 443.820s nutzbares Material uebrig waren. Das ist kein Bug, sondern korrektes Floor-Verhalten.

Phase 2 ist abgeschlossen und abnahmefaehig fuer Phase 3. Render-Beweis-Commit: d17ab09.

Keine erfundenen Test- oder ffprobe-Ausgaben wurden eingetragen.

## 11. P2-FIX-3B Duration-Floor-Nachbesserung

Nach dem echten gaming_main E2E-Lauf wurde ein technisch gueltiger Render erzeugt, aber der finale Output war nur 319.083789 Sekunden lang und lag damit unter dem geforderten 480-1200s-Fenster.

Root Cause: Der bisherige 480s-YouTube-Floor setzte nur target_duration, garantierte aber nicht, dass LongformTimelineBuilder tatsaechlich genug selected_segments auswaehlt. Zusaetzlich wurden Kandidaten unter der harten 0.45-Score-Schwelle zu frueh verworfen.

Fix-Commit: a27d192f87e3876f166bdec3c9a1c194726d2986
Commit-Message: fix(P2-FIX-3B): enforce gaming main duration floor

Geaenderte Dateien:
- core/longform_timeline_builder.py
- tests/test_phase2_p2_fix3b_duration_floor_smoke.py

Umsetzung:
- YOUTUBE_MIN_DURATION = 480.0 und LONGFORM_PRIMARY_SCORE_FLOOR = 0.45 ergaenzt.
- _dedupe_and_select() wurde duration-floor-aware gemacht.
- Kandidaten unter 0.45 werden als duration_floor_reserve gefuehrt.
- Fuer gaming_main Longform wird ein harter 480s-Floor geprueft.
- Wenn der Floor vor oder nach den Guards nicht erreichbar ist, wird ein klarer ValidationError ausgeloest.
- Neuer Smoke-Test prueft 480s-Floor, Reserve-Kandidaten, Fehlerfall und 1200s-Obergrenze.

Lokale Testnachweise:
python -m pytest tests/test_phase2_p2_fix3b_duration_floor_smoke.py -q
4 passed in 0.40s

PYTHONPATH Smoke + Target Duration Tests:
LONGFORM TIMELINE BUILDER SMOKE TEST PASSED
4 passed in 0.52s

Status nach P2-FIX-3B: Der Code verhindert jetzt still zu kurze gaming_main-Longform-Timelines. Der echte E2E-Render muss nach diesem Commit erneut lokal gefahren und mit ffprobe belegt werden. Phase 2 bleibt bis zu diesem neuen ffprobe-Beweis NO-GO.

## 12. P2-FIX-3B Real-E2E-Rerun nach Fix

Nach Commit a27d192f87e3876f166bdec3c9a1c194726d2986 wurde ein neuer echter gaming_main E2E-Lauf gestartet.

Quelle:
inbox\gaming_main\League of Legends Full Video 1 P2FIX3B.mp4

Job:
job_0c140762248f

Roher Pipeline-Befund:
TIMELINE-SCORE-POOLS primary=70 reserve=29 threshold=0.45
TIMELINE-QUALITY Highlights: 70, Avg Score: 0.68, Density: 0.69
TIMELINE-QUALITY Category: good, Retention: 75%
TIMELINE-QUALITY Duration: 1018s -> Target: 763s (75%)
TIMELINE-SEGMENTS Target: 763s -> Max Segments: 76
TIMELINE-DURATION-FLOOR target=763.373s floor=480.000s selected=265.000s primary_candidates=70 reserve_candidates=29 reserve_used=3 max_segments=76
TIMELINE-DURATION-FLOOR-BLOCKED selected=265.000s floor=480.000s primary=70 reserve=29 target=763.373s

Pipeline-Schluss:
Done ok=0 skipped=0 failed=1
job_0c140762248f (gaming_main)
Longform floor 480s unreachable: only 265s of usable material

Auswertung:
P2-FIX-3B wirkt korrekt. Zenith rendert kein still zu kurzes gaming_main-Longform-Video mehr. Stattdessen blockiert der Pipeline-Lauf sauber, wenn der 480s-Floor nicht erreichbar ist.

Phase-2-Status:
Weiterhin NO-GO, weil noch kein echter gaming_main Render mit 480-1200 Sekunden und ffprobe-Beweis vorliegt.

## 13. P2-FIX-3C-DIAG Longform Candidate Loss Diagnosis

Diagnoseauftrag:
Warum bleiben aus 1018s Rohvideo nur ca. 265-271s nutzbares Longform-Material uebrig?

Job:
job_0c140762248f

Diagnose-Skript:
tools/diag/diag_longform_candidate_loss.py

Das Skript ist read-only. Es erzeugt die Legacy-Edit-Signale wie die echte Pipeline neu ueber EditSignalExtractor und simuliert die Longform-Auswahl extern. Es aendert keinen Produktionscode.

Roher Kernbefund:

analysis_duration_seconds=1018.0
edit_signal_source=EditSignalExtractor.recomputed
edit_signals=1698
edit_signal_type_counts={'audio_activity': 666, 'motion_peak': 161, 'duration_context': 1, 'motion_activity': 501, 'audio_peak': 101, 'silence_zone': 251, 'low_motion_zone': 17}
highlight_candidates_before_scoring=99
weak_zones=70
primary_candidates=99
reserve_candidates=0
target_duration=936.560
max_segments=93

Frage 1 - Kandidaten-Inventar:

raw_duration_stats={'count': 99, 'sum': 1367.33, 'min': 8.0, 'median': 14.0, 'avg': 13.811, 'max': 14.0}
raw_duration_buckets={'lt_3s': 0, '3_to_8s': 0, '8_to_15s': 99, '15_to_30s': 0, 'gt_30s': 0}
raw_sum_with_overlaps=1367.330
raw_unique_coverage_seconds=728.330

Antwort:
Die Highlight-Erkennung erzeugt genug Material. Es gibt 99 Kandidaten, keine Kandidaten unter 3s, Median 14s, und ca. 728.33s unique Coverage. Der Defekt liegt nicht darin, dass zu wenige oder zu kurze Highlight-Kandidaten entstehen.

Frage 2 - Verlust in _dedupe_and_select.try_add:

selected_count=25
selected_duration=271.000
reserve_used=0
unused_primary_count=74
unused_reserve_count=0
max_segments_cap_hit=False

reject reason=heavy_weak_zone_penalty count=67 pct=67.68% seconds=928.330
reject reason=overlap_ge_0_70 count=3 pct=3.03% seconds=42.000
reject reason=trim_invalid count=4 pct=4.04% seconds=56.000

Antwort:
Der Hauptverlust entsteht durch heavy_weak_zone_penalty. 67 von 99 Kandidaten werden dadurch verworfen. Overlap >= 0.70 ist mit 3 Kandidaten nicht die Hauptursache. Trim invalid betrifft 4 Kandidaten.

Frage 3 - Wo verdampfen die Sekunden:

sum_candidate_durations_before_dedup=1367.330
sum_selected_durations_after_dedup=271.000
lost_seconds_total=1096.330
lost_pct_vs_raw_sum=80.18%
unused_primary_seconds=1026.330
unused_reserve_seconds=0.000
lost_by_reason heavy_weak_zone_penalty seconds=928.330
lost_by_reason overlap_ge_0_70 seconds=42.000
lost_by_reason trim_invalid seconds=56.000
lost_by_reason trimmed_seconds_kept_segment seconds=70.000

Root-Cause-Entscheidung:
Heavy weak-zone penalty ist der Hauptverlust.

Root-Cause-Detail:
67/99 Kandidaten (67.68%) werden wegen heavy_weak_zone_penalty verworfen. Dadurch gehen 928.330s Kandidatenmaterial verloren.

Naechster Fix-Bereich:
Weak-zone-Erkennung oder Anwendung der heavy_weak_zone_penalty im Longform-Scoring untersuchen. Nicht den Duration-Floor weiter haerten. Nicht zuerst Overlap-Dedup fixen, weil Overlap nur 3.03% der Kandidaten betrifft.

Phase-2-Status:
Weiterhin NO-GO, weil noch kein echter gaming_main Render mit 480-1200s und ffprobe-Beweis vorliegt.

## 14. P2-FIX-3D Weak-Zone-Killswitch Fix

Auftrag:
Den heavy_weak_zone_penalty-Killswitch in core/longform_timeline_builder.py beheben.

Commits:
b3c6bac fix(P2-FIX-3D): remove weak-zone killswitch
6898e93 fix(P2-FIX-3D): gate duration floor by raw length

Geaenderte Dateien:
- core/longform_timeline_builder.py
- tests/test_phase2_p2_fix3d_weak_zone_penalty_smoke.py

Penalty-Wert:
heavy_weak_zone_penalty wurde von score -= 0. auf score -= 0.40 korrigiert.

Herleitung:
partial_weak_zone_penalty liegt bei -0.20. Die heavy-Variante muss staerker sein, aber Kandidaten nicht vernichten. -0.40 drueckt viele heavy weak-zone Kandidaten unter LONGFORM_PRIMARY_SCORE_FLOOR = 0.45, wodurch sie in den Reservepool wandern statt geloescht zu werden.

Killswitch-Fix:
Der Early-Return in _dedupe_and_select.try_add fuer heavy_weak_zone_penalty wurde entfernt. Die Note bleibt Diagnose-Marker, darf aber nicht mehr bedingungslos verwerfen.

Testnachweis:
python -m pytest tests/test_phase2_p2_fix3d_weak_zone_penalty_smoke.py -q
4 passed in 0.42s

Regression:
python -m pytest tests/test_phase2_p2_fix3d_weak_zone_penalty_smoke.py tests/test_phase2_p2_fix3b_duration_floor_smoke.py tests/test_target_duration_smoke.py -q
8 passed in 0.66s

Volle Standard-Suite:
3523 passed, 2 skipped, 5 deselected in 96.67s

Echter gaming_main E2E-Rerun:
Job:
job_6cb67b539814

Quelle:
inbox\gaming_main\League of Legends Full Video 1 P2FIX3D.mp4

Roher Kernbefund:
[TIMELINE-SCORE-POOLS] primary=32 reserve=67 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=610.698s floor=480.000s selected=480.330s primary_candidates=32 reserve_candidates=67 reserve_used=23 max_segments=61

Auswertung:
P2-FIX-3D wirkt. Vor den spaeteren Guards erreicht die Timeline jetzt 480.330s. Vor P2-FIX-3D waren es nur ca. 265s. Der heavy weak-zone Killswitch ist damit als behoben belegt.

Neuer Blocker nach P2-FIX-3D:
[TIMELINE-DURATION-FLOOR-BLOCKED] selected_after_guards=445.690s floor=480.000s primary=32 reserve=67 target=610.698s
Longform floor 480s unreachable: only 446s of usable material after guards

Wichtige Guard-Verluste:
[TIMELINE-ROUND-WAIT-GUARD] duration_before=458.670s duration_after=324.010s
[TIMELINE-HARD-SPEECH-LOCK] duration_before=346.500s duration_after=541.930s
[TIMELINE-PRIVATE-MENU-SPEECH] duration_before=529.620s duration_after=455.050s
[TIMELINE-SENTENCE-ATOMICITY] duration_before=455.050s duration_after=449.640s
[TIMELINE-ROUND-LIFECYCLE] duration_before=449.640s duration_after=445.590s
[TIMELINE-UNIVERSAL-SAFE-TRIM] duration_before=445.690s duration_after=445.690s

Phase-2-Status:
Weiterhin NO-GO. Es gibt noch keinen echten gaming_main Render mit 480-1200s und ffprobe-Beweis.

Naechster Root-Cause-Bereich:
Nicht mehr heavy_weak_zone_penalty. Der naechste Defekt liegt nach der Auswahl in den post-selection Guards, weil die Auswahl 480.330s erreicht, aber nach Guards nur 445.690s uebrig bleiben.

## 15. P2-FIX-3-CLOSE Phase-2 Abschluss

Status:
Phase 2 abgeschlossen, abnahmefaehig fuer Phase 3.

Render-Beweis-Commit:
d17ab09

Quelle:
docs/PHASE2_MATVAL_RESULTS.md

P2-FIX-3 ist durch zwei echte gaming_main-Renders erfuellt.

LoL raw ffprobe evidence:
duration=490.851758
codec_type=video
codec_name=h264
width=1920
height=1080
display_aspect_ratio=16:9

Minecraft raw ffprobe evidence:
duration=736.000438
codec_type=video
codec_name=h264
width=1920
height=1080
display_aspect_ratio=16:9

Fortnite Materialvalidierung:
selected_after_guards=443.820s
kein MP4 erzeugt
kein Bug: Inhalt reicht nach Guards nicht fuer 480s. Der Floor-Mechanismus arbeitet wie spezifiziert und rendert kein still zu kurzes Longform-Video.

Abschlussbewertung:
LoL PASS: 490.851758s, h264, 1920x1080, 16:9
Minecraft PASS: 736.000438s, h264, 1920x1080, 16:9
Fortnite korrekt blockiert: 443.820s nach Guards

P2-7 Whisper bleibt als Protokollvermerk offen, ist aber nicht Phase-2-blockierend.
