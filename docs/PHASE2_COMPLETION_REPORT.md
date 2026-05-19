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

Offen: Ein echter `gaming_main` End-to-End-Render über `pipeline_runner.py` wurde in diesem Chat nicht ausgeführt. Es liegt bisher kein roher `ffprobe`-Output eines echten finalen `gaming_main`-Renders vor.

Kein ffprobe-Output wurde erfunden.

Lokal nachzutragender Ablauf:

```powershell
cd D:\Zenith
# echtes gaming_main-Rohvideo durch pipeline_runner.py fahren
# danach fertigen Render mit ffprobe prüfen:
ffprobe -hide_banner -show_format -show_streams "<PFAD_ZUM_FINAL_RENDER>.mp4"
```

Der rohe `ffprobe`-Output muss zeigen:

- Container-/Formatdaten
- Gesamtdauer zwischen 480 und 1200 Sekunden
- Video-Stream mit 16:9-Seitenverhältnis
- mindestens einen Audio-Stream

Falls Profanity/Censor-SFX im Video vorhanden ist, muss zusätzlich ein roher Audioenergie-Nachweis über das gemappte Censor-Zeitfenster ergänzt werden, zum Beispiel mit `volumedetect` oder `astats`.

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

Dieser Report enthält die geforderten acht Kernpunkte. Die Code-/Doku-Nachbesserungen P2-FIX-1, P2-FIX-4 und P2-FIX-5 wurden umgesetzt. P2-FIX-2 ist durch lokale rohe pytest-Schlussbalken belegt. P2-FIX-3 bleibt offen, weil noch kein echter `gaming_main`-Pipeline-Render mit rohem `ffprobe`-Output vorliegt.

Keine erfundenen Test- oder ffprobe-Ausgaben wurden eingetragen.
