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

Ein echter `gaming_main` End-to-End-Lauf wurde auf der Nutzer-Maschine ausgeführt:

```powershell
cd D:\Zenith
python pipeline_runner.py
```

Quelle:

```text
inbox\gaming_main\League of Legends Full Video 1.mp4
```

Job:

```text
job_9ba111149e70
```

Der Pipeline-Lauf erzeugte und exportierte eine finale MP4:

```text
D:\Zenith\exports\gaming_main\job_9ba111149e70\job_9ba111149e70_v1_final.mp4
```

Pipeline-Schlussnachweis:

```text
[gaming_pipeline] RENDER    job_9ba111149e70  → output\job_9ba111149e70_final.mp4
[gaming_pipeline] SUBTITLES job_9ba111149e70  done
[gaming_pipeline] META      job_9ba111149e70  title='Unfassbarer Gaming Moment 😱🔥'
[gaming_pipeline] VALIDATE  job_9ba111149e70  status=passed
[gaming_pipeline] VALIDATE_DETAIL job_9ba111149e70 status=passed reason=all blocking checks passed
[PHASE-2B-STABILIZATION] status=passed_with_known_warnings ready=true artifacts=8/8 timeline_segments=12 final_review_segments=12 warnings=2
[gaming_pipeline] DONE      job_9ba111149e70  status=approval_pending
[pipeline_runner] EXPORT_VERSION job_9ba111149e70 version=1 file=job_9ba111149e70_v1_final.mp4
[pipeline_runner] COPIED   1 file(s) to export
[pipeline_runner] CLEANUP  Deleted 1 temporary file(s) from output/
[pipeline_runner] EXPORT    job_9ba111149e70  → exports\gaming_main\job_9ba111149e70
[pipeline_runner] JOB_JSON  job_9ba111149e70  path=exports\gaming_main\job_9ba111149e70\job.json

[pipeline_runner] Done ? ok=1  skipped=0  failed=0
  ?  job_9ba111149e70  (gaming_main)
```

ffprobe-Befehl:

```powershell
D:\Tools\ffmpeg\bin\ffprobe.exe -hide_banner -show_format -show_streams "D:\Zenith\exports\gaming_main\job_9ba111149e70\job_9ba111149e70_v1_final.mp4"
```

Roher ffprobe-Output:

```text
Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'D:\Zenith\exports\gaming_main\job_9ba111149e70\job_9ba111149e70_v1_final.mp4':
  Metadata:
    major_brand     : isom
    minor_version   : 512
    compatible_brands: isomiso2avc1mp41
    encoder         : Lavf62.13.101
  Duration: 00:05:19.08, start: 0.000000, bitrate: 5267 kb/s
  Stream #0:0[0x1](und): Video: h264 (High) (avc1 / 0x31637661), yuv420p(progressive), 1920x1080 [SAR 1:1 DAR 16:9], 5063 kb/s, 59.98 fps, 60 tbr, 15360 tbn, start 0.021029 (default)
    Metadata:
      handler_name    : VideoHandler
      encoder         : Lavc62.29.101 libx264
  Stream #0:1[0x2](eng): Audio: aac (LC) (mp4a / 0x6134706D), 48000 Hz, stereo, fltp, 192 kb/s (default)
    Metadata:
      handler_name    : #Mainconcept MP4 Sound Media Handler
[STREAM]
index=0
codec_name=h264
codec_long_name=H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
profile=High
codec_type=video
codec_tag_string=avc1
codec_tag=0x31637661
mime_codec_string=avc1.64002a
width=1920
height=1080
coded_width=1920
coded_height=1080
has_b_frames=2
sample_aspect_ratio=1:1
display_aspect_ratio=16:9
pix_fmt=yuv420p
level=42
color_range=unknown
color_space=unknown
color_transfer=unknown
color_primaries=unknown
chroma_location=left
field_order=progressive
is_avc=true
nal_length_size=4
id=0x1
r_frame_rate=60/1
avg_frame_rate=73489920/1225201
time_base=1/15360
start_pts=323
start_time=0.021029
duration_ts=4900804
duration=319.062760
bit_rate=5063297
max_bit_rate=N/A
bits_per_raw_sample=8
nb_frames=19138
nb_read_frames=N/A
nb_read_packets=N/A
extradata_size=46
DISPOSITION:default=1
DISPOSITION:dub=0
DISPOSITION:original=0
DISPOSITION:comment=0
DISPOSITION:lyrics=0
DISPOSITION:karaoke=0
DISPOSITION:forced=0
DISPOSITION:hearing_impaired=0
DISPOSITION:visual_impaired=0
DISPOSITION:clean_effects=0
DISPOSITION:attached_pic=0
DISPOSITION:timed_thumbnails=0
DISPOSITION:non_diegetic=0
DISPOSITION:captions=0
DISPOSITION:descriptions=0
DISPOSITION:metadata=0
DISPOSITION:dependent=0
DISPOSITION:still_image=0
DISPOSITION:multilayer=0
TAG:language=und
TAG:handler_name=VideoHandler
TAG:encoder=Lavc62.29.101 libx264
[/STREAM]
[STREAM]
index=1
codec_name=aac
codec_long_name=AAC (Advanced Audio Coding)
profile=LC
codec_type=audio
codec_tag_string=mp4a
codec_tag=0x6134706d
mime_codec_string=mp4a.40.2
sample_fmt=fltp
sample_rate=48000
channels=2
channel_layout=stereo
bits_per_sample=0
initial_padding=0
id=0x2
r_frame_rate=0/0
avg_frame_rate=0/0
time_base=1/48000
start_pts=0
start_time=0.000000
duration_ts=15315108
duration=319.064750
bit_rate=192069
max_bit_rate=N/A
bits_per_raw_sample=N/A
nb_frames=14967
nb_read_frames=N/A
nb_read_packets=N/A
extradata_size=5
DISPOSITION:default=1
DISPOSITION:dub=0
DISPOSITION:original=0
DISPOSITION:comment=0
DISPOSITION:lyrics=0
DISPOSITION:karaoke=0
DISPOSITION:forced=0
DISPOSITION:hearing_impaired=0
DISPOSITION:visual_impaired=0
DISPOSITION:clean_effects=0
DISPOSITION:attached_pic=0
DISPOSITION:timed_thumbnails=0
DISPOSITION:non_diegetic=0
DISPOSITION:captions=0
DISPOSITION:descriptions=0
DISPOSITION:metadata=0
DISPOSITION:dependent=0
DISPOSITION:still_image=0
DISPOSITION:multilayer=0
TAG:language=eng
TAG:handler_name=#Mainconcept MP4 Sound Media Handler
[/STREAM]
[FORMAT]
filename=D:\Zenith\exports\gaming_main\job_9ba111149e70\job_9ba111149e70_v1_final.mp4
nb_streams=2
nb_programs=0
nb_stream_groups=0
format_name=mov,mp4,m4a,3gp,3g2,mj2
format_long_name=QuickTime / MOV
start_time=0.000000
duration=319.083789
size=210105162
bit_rate=5267711
probe_score=100
TAG:major_brand=isom
TAG:minor_version=512
TAG:compatible_brands=isomiso2avc1mp41
TAG:encoder=Lavf62.13.101
[/FORMAT]
```

### E2E-Auswertung

- **Echter Render erzeugt:** Ja.
- **Container/Format:** MP4/MOV, `format_name=mov,mp4,m4a,3gp,3g2,mj2`.
- **Video vorhanden:** Ja, Stream `index=0`, `codec_name=h264`.
- **Auflösung/Seitenverhältnis:** Ja, `1920x1080`, `display_aspect_ratio=16:9`.
- **Audio vorhanden:** Ja, Stream `index=1`, `codec_name=aac`, `48000 Hz`, `stereo`.
- **Dauer:** Nein für Phase-2-Abschluss. `duration=319.083789` Sekunden bzw. `00:05:19.08`.
- **Gefordertes Dauerfenster:** 480–1200 Sekunden.
- **Ergebnis P2-FIX-3:** Nicht bestanden, weil der echte Render nur ca. 5:19 Minuten lang ist und damit unter der 8-Minuten-Monetarisierungsgrenze liegt.
- **Censor-SFX-Nachweis:** Nicht erforderlich für diesen Lauf, weil der Pipeline-Log `PROFANITY_CENSOR_DONE` mit `reason=no_profanity_censor_candidates` meldete und der Nutzer bestätigte, dass im Video keine Beleidigungen vorkamen.

## 8. Offener Punkt: Realer Whisper-Lauf

Der reale Whisper-Lauf mit echtem `faster-whisper` ohne Test-Modus ist nur lokal auf der Nutzer-Maschine belegt. Er wurde nicht in einer Umgebung mit Netz-/Modell-Cache vom Prüf-Chat reproduziert. Dieser Punkt bleibt offen, bis ein Prüferlauf mit passenden Modell-/Cache-Voraussetzungen oder ein eindeutig übertragbares Artefakt vorliegt.

## 9. P2-FIX-5 Regressionswächter

P2-FIX-5 wurde umgesetzt. Neuer Standard-Smoke-Test:

```text
tests/test_phase2_p2_fix_encoder_assertion_guard_smoke.py
```

Der Test scannt `tests/test_final_render_driver_smoke.py` und verhindert, dass die stale Assertion `ctx["codec_video"] == "h264_nvenc"` zurückkehrt. Außerdem prüft er, dass `_resolve_video_encoder`, `resolved["codec"]` und `resolved["mode"]` im Test verwendet werden.

P2-FIX-5 Commit: `a26089b84df2772322c30f188d3b5f4ee8549acc`.

## 10. Abschlussstatus dieses Reports

Dieser Report enthält die geforderten acht Kernpunkte. Die Code-/Doku-Nachbesserungen P2-FIX-1, P2-FIX-4 und P2-FIX-5 wurden umgesetzt. P2-FIX-2 ist durch lokale rohe pytest-Schlussbalken belegt. P2-FIX-3 wurde real ausgeführt und erzeugte einen technisch gültigen MP4-Render mit 16:9-Video und Audiospur, verfehlte aber das geforderte Dauerfenster von 480–1200 Sekunden. Phase 2 bleibt deshalb NO-GO.

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

