# STOPP P4.5-FINAL - GPU-Thermal-/SM-Beweis nicht erreicht

## Status

STOPP. Phase 4 + Phase 4.5 kann nicht als abgeschlossen markiert werden, weil im finalen Vollrender noch harte GPU-Beweis-Metriken rot sind.

## Verifizierter HEAD

`44e125dea055b966ed1d197a903d4610840c1b30 fix(P4.5-final): raise performance nvenc preset for render-stage utilization`

## Letzter Vollrender

- Job: `job_e8227c99248c`
- Input: `learning_corpus/pairs/pair_001/raw.mp4`
- Command: `python pipeline_runner.py learning_corpus\pairs\pair_001\raw.mp4 --power-profile performance`
- Exitcode: `0`
- Dauer: `00:23:58.8003900`
- Longform: `exports/gaming_main/job_e8227c99248c/job_e8227c99248c_v1_final.mp4`
- Shorts: 5 gueltige MP4s
- Job JSON: `1.31 MB` Export, `1.08 MB` Persistenz

## Metriken

| Metrik | Ziel | Erreicht | Status |
|---|---:|---:|---|
| Render-Dauer | < 30:00 | 23:58.8 | PASS |
| pytest | 0 failed | 3763 passed, 2 skipped, 24 deselected | PASS |
| Pipeline exit | 0 | 0 | PASS |
| Longform + Shorts | 1 + mind. 3 | 1 + 5 | PASS |
| Audio | vorhanden | AAC stereo im Longform | PASS |
| Job-Datei | < 30 MB | 1.31 MB Export / 1.08 MB Persistenz | PASS |
| CPU-Auslastung Durchschnitt | < 80% | 5.06% | PASS |
| CPU-Auslastung Max | < 95% | 35% | PASS |
| RAM Peak | < 50 GB | 18.46 GB | PASS |
| VRAM Peak | < 20 GB | 4.46 GB | PASS |
| GPU enc Durchschnitt Render-Samples | > 20% | 57.96% (`enc > 20`) | PASS |
| GPU sm Durchschnitt Render-Samples | > 30% | 25.97% (`enc > 20`) | FAIL |
| GPU Temperatur Max | > 50C und < 80C | 42C | FAIL |
| GPU Temperatur Durchschnitt Render-Samples | > 45C | 39.63C (`enc > 20`) | FAIL |
| CPU Temperatur | < 75C avg / < 85C max | nicht messbar via WMI auf diesem System | BLOCKED |

## Was versucht wurde

1. `d66c8c5` - EditSignalExtractor nutzt vorhandene RMS-/Motion-Analysen statt MoviePy-Rohscan.
   - Ergebnis: `edit_signals` von ca. 993s auf ca. 0.7s reduziert.

2. `a89301e` - Cached-Audio-Silence-Klassifikation entschaerft.
   - Ergebnis: zu aggressive Silence-Penalties reduziert, aber Timeline-Floor blieb erst rot.

3. `5685203` - Cached-Audio-Fenster auf alte 4s/1s-Window-Semantik gebracht.
   - Ergebnis: Longform-Floor wieder gruen, Vollrender erfolgreich.

4. `dbe43aa` - Shorts-Emoji-Overlay CPU-frame-safe gemacht.
   - Ergebnis: nicht-fataler FFmpeg-Fehler im Shorts-Overlay behoben.

5. `44e125d` - Performance-NVENC auf `p7` angehoben und Shorts-NVENC-Preset explizit gesetzt.
   - Ergebnis: Encoder-Auslastung stieg deutlich, Temperatur und SM-Durchschnitt bleiben rot.

## Diagnose

Die produktive Pipeline nutzt NVENC und CUDA-Skalierung, aber die finale Komposition besteht weiterhin zu grossen Teilen aus CPU-Filtern:

- `crop` und `overlay` laufen in den aktuellen FinalRenderDriver-Filterketten auf CPU-Frames.
- CUDA wird vor allem fuer `scale_cuda` und NVENC-Encoding genutzt.
- FFmpeg-Build enthaelt `scale_cuda`, `overlay_cuda`, `pad_cuda`, aber kein `crop_cuda` und kein `scale_npp/crop_npp`.
- Zwei parallele Segment-Render-Worker sind aktiv. Mehr wuerde das P4.5-12 NVENC-Session-Limit verletzen.
- Die RTX 4090 bleibt bei dieser Last thermisch sehr kuehl: Max 42C trotz 24-Minuten-Vollrender.

Damit ist der Temperaturwert kein verlaesslicher Beweis fuer GPU-Arbeit auf dieser Maschine. Die dmon/resource-Daten beweisen GPU-Encoding, aber nicht die geforderte thermische Schwelle.

## Naechste sinnvolle Strategie

User-Entscheidung erforderlich:

1. Akzeptanzkriterium anpassen:
   - GPU-Temp-Beweis durch dmon/resource-Auslastung ersetzen, z.B. `enc > 20%` und `sm > 20-25%` waehrend Render-Samples.

2. FFmpeg-GPU-Compositor nachruesten:
   - FFmpeg mit NPP-Filtern (`scale_npp`, idealerweise Crop/Composite-Pfad) oder Vulkan/OpenCL-Filterpfad bereitstellen.
   - Danach FinalRenderDriver-Filterketten auf echte GPU-Komposition umbauen.

3. NVENC-Session-Limit bewusst lockern:
   - Segment-Worker auf 3+ erhoehen, um GPU-Last/Temperatur zu steigern.
   - Das widerspricht aber der P4.5-12-Stabilitaetsvorgabe `max 2 gleichzeitige NVENC-Sessions`.

## STOPP-Grund

Nach mehreren finalen Iterationen ist alles ausser GPU-SM-/GPU-Temperatur-Beweis gruen. Eine weitere Iteration ohne geaenderte Akzeptanz oder neuen FFmpeg-GPU-Compositor wuerde nur versuchen, die GPU kuenstlich zu erhitzen oder das NVENC-Session-Limit zu brechen.
