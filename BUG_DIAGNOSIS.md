# BUG_DIAGNOSIS — Reframe-Bug: "zwei Hälften nebeneinander"

Erstellt: 2026-04-29  
Job: `job_cd218a143650`  
Source: `inbox\gaming_main\Rocket_League_compressed.mp4`  
Symptom: Endvideo (1920×1080) zeigt beide Hälften des OBS-Recordings nebeneinander — statt Gameplay groß + Facecam-PiP oben links.

---

## 1. Vollständiger Code-Pfad

```
app.py:741
  └─ ReframingCore().build_plan(source_aspect_ratio="32:9")   ← hardcoded, nie aus Videogröße ermittelt
       └─ FacecamGameplaySeparator.classify_segment()          [facecam_gameplay_separator.py:11]
       └─ _layout_kind_for_focus()                             [reframing_core.py:26]
       └─ _crop_window()                                       [reframing_core.py:46]
       └─ FramingInstruction(layout_kind, crop_window)         [gespeichert, aber nicht genutzt]

final_render_driver.py:223
  src_w, src_h = _get_video_dimensions(source)                ← korrekt ermittelt
  └─ für jedes Segment:
       └─ _build_filter_complex(seg, reframe_plan, ..., src_w, src_h)
            └─ src_w, src_h werden IGNORIERT                   ← BUG 1
            └─ instr.crop_window wird IGNORIERT                ← BUG 2
            └─ hardcoded: crop=1920:1080:1920:0               ← bricht bei falscher Source-Breite
       └─ _extract_segment(..., filter_complex, ...)
```

---

## 2. Segment-Analyse: focus_kind und layout_kind pro Segment

Quelle: `FacecamGameplaySeparator.classify_segment()` — Standardpfade ohne bekannte candidate_kind/signal_tags.

| # | Segment-ID | Rolle | Zeitraum | focus_kind | Code-Zeile | layout_kind | Filter-Pfad |
|---|---|---|---|---|---|---|---|
| 1 | seg_7dcbbafcc7ec | hook | 50–62.5s | `facecam` | separator.py:34 | `facecam_emphasis` | Sonderfall Z.97 |
| 2 | seg_21252bd4722c | peak | 84–96s | `gameplay` | separator.py:49 | `gameplay_crop` | Standardfall Z.104 |
| 3 | seg_d25244b164d0 | bridge | 94–106s | `balanced` | separator.py:67 | `balanced_split` | Standardfall Z.104 |
| 4 | seg_99ed4b73c5b9 | bridge | 165–175s | `balanced` | separator.py:67 | `balanced_split` | Standardfall Z.104 |
| 5 | seg_5cf3a64f92f1 | bridge | 190–200s | `balanced` | separator.py:67 | `balanced_split` | Standardfall Z.104 |
| 6 | seg_d63ab21bf407 | payoff | 195–205s | `balanced` | separator.py:63 | `balanced_split` | Standardfall Z.104 |

**Ergebnis:** 1 Segment → `facecam_emphasis`, 5 Segmente → identischer PiP-Filter (kein expliziter Handler für `gameplay_crop` oder `balanced_split`).

---

## 3. Welcher Filter-Complex wird gebaut?

### Segment 1 — layout_kind `"facecam_emphasis"` (final_render_driver.py:97–102)

```python
if layout_kind == "facecam_emphasis":
    fc = (
        "[0:v]crop=1920:1080:0:0,"
        "scale=1920:1080[out]"
    )
    return fc, "[out]"
```

Erzeugter String:
```
[0:v]crop=1920:1080:0:0,scale=1920:1080[out]
```

Für 3840×1080: x=0, w=1920 → linke Hälfte (Facecam) korrekt extrahiert.  
Für 1920×1080: x=0, w=1920 → gesamter Frame (beide Hälften squished) wird durchgereicht.

---

### Segmente 2–6 — Standardfall, layout_kind `"gameplay_crop"` / `"balanced_split"` (final_render_driver.py:104–114)

`_build_filter_complex()` hat **kein `elif`** für `"gameplay_crop"` oder `"balanced_split"`. Beide landen beim selben PiP-Filter:

```python
# Kein Handler für "gameplay_crop", "balanced_split", "full_gameplay".
# Alle drei fallen durch zum identischen Block:
PIP_W, PIP_H = 480, 270
PIP_X, PIP_Y = 32, 32

fc = (
    "[0:v]split=2[gp_src][fc_src];"
    "f"[gp_src]crop={src_w//2}:1080:{src_w//2}:0,scale=1920:1080[gp];""   # Z.110 — hardcoded 1920
    f"[fc_src]crop=1920:1080:0:0,scale={PIP_W}:{PIP_H}[fc];"
    f"[gp][fc]overlay={PIP_X}:{PIP_Y}[out]"
)
```

Erzeugter String (für alle 5 Nicht-Hook-Segmente identisch):
```
[0:v]split=2[gp_src][fc_src];
[gp_src]crop=1920:1080:1920:0,scale=1920:1080[gp];
[fc_src]crop=1920:1080:0:0,scale=480:270[fc];
[gp][fc]overlay=32:32[out]
```

---

## 4. Antwort auf die Hypothese: crop vs. scale-ohne-crop

> *Prüfe ob der Filter wirklich `crop=1920:1080:1920:0` macht, oder ob er das ganze 3840-breite Frame nimmt und auf 1920 skaliert.*

**Der Filter-String enthält `crop=1920:1080:1920:0` — der Crop ist im Code vorhanden.**  
Die `scale=1920:1080` im PiP-Filter wird erst NACH dem Crop angewendet; für eine echte 3840×1080-Source ist die gesamte Kette korrekt.

**Jedoch:** Die 1920 in `crop=1920:1080:1920:0` ist eine **hardcodierte Konstante**, nicht `src_w // 2`. Wenn `_get_video_dimensions()` eine andere Breite zurückgibt (s.u.), passiert genau das beschriebene Problem.

---

## 5. Der eigentliche Bug: `src_w` / `src_h` werden empfangen, aber vollständig ignoriert

### Fundstelle: `final_render_driver.py:80–87` (Signatur) und `Z.99, 110–111` (Nutzung)

```python
def _build_filter_complex(
    self,
    segment: TimelineSegment,
    reframe_plan: ReframePlan | None,
    dynamic_edit_plan: DynamicEditPlan | None,
    src_w: int,     # ← empfangen, aber…
    src_h: int,     # ← empfangen, aber…
) -> tuple[str, str]:
    ...
    # Nirgendwo im Funktionskörper taucht src_w oder src_h auf.
    # Stattdessen: hardcoded 1920 an drei Stellen:
    "[0:v]crop=1920:1080:0:0,..."          # Z.99  — facecam_emphasis
    "[gp_src]crop=1920:1080:1920:0,..."    # Z.110 — PiP: Gameplay-Crop
    "[fc_src]crop=1920:1080:0:0,..."       # Z.111 — PiP: Facecam-Crop
```

### Warum das den Splitscreen erzeugt

Der Dateiname `Rocket_League_compressed.mp4` enthält "compressed". Wahrscheinlichste Ursache: Das OBS-Recording war 3840×1080 (32:9), wurde aber zur Speicherreduktion auf **1920×1080 herunterskaliert** — beide Hälften squished auf je 960px Breite. `ffprobe` meldet korrekt `1920,1080`. `_get_video_dimensions()` gibt `(1920, 1080)` zurück; dieser Wert wird aber ignoriert.

**Was FFmpeg mit `crop=1920:1080:1920:0` auf einem 1920px breiten Frame macht:**

```
x = 1920, out_w = 1920  →  x + out_w = 3840 > source_w = 1920
FFmpeg klemmt: x_eff = max(0, source_w − out_w) = max(0, 1920 − 1920) = 0
Effektiv: crop=1920:1080:0:0 — der gesamte 1920×1080-Frame wird durchgereicht.
```

Dieser Frame enthält beide squished Hälften (Facecam links 960px, Gameplay rechts 960px). Er wird als Gameplay-Hintergrund genutzt. Die PiP-Facecam zeigt dasselbe. Ergebnis: **1920×1080-Output mit beiden Hälften nebeneinander** — das gemeldete Symptom.

---

## 6. Bugübersicht nach Schwere

| # | Bug | Datei:Zeile | Auswirkung |
|---|---|---|---|
| **1 (Hauptursache)** | `src_w`/`src_h` in `_build_filter_complex()` empfangen aber nie benutzt; alle Crops hardcoded auf 1920 | `final_render_driver.py:85–86, 99, 110–111` | **Splitscreen** bei Source ≠ 3840px Breite |
| **2 (Nebenursache)** | `source_aspect_ratio="32:9"` in `app.py:745` hardcoded — nie aus tatsächlicher Videodimension ermittelt | `app.py:745` | ReframePlan ist für komprimierte 16:9-Source konzeptionell falsch |
| **3 (Strukturell)** | `instr.crop_window` (normalisierte Koordinaten aus `reframing_core.py:46–75`) werden in `_build_filter_complex()` nie gelesen | `final_render_driver.py:93–94` | `ReframingCore._crop_window()`-Logik ist wirkungslos; verhindert einen auflösungsunabhängigen Fix |
| **4 (Diagnostisch)** | Context-JSON enthält weder `src_w`/`src_h` noch `detected_aspect_ratio` | `final_render_driver.py:241–276` | Nachträgliche Diagnose dieses Bugs erschwert |

---

## 7. Entfernter Code als Ursache

Im Git-Commit `555f0b2` wurde `patch_render_driver_v2.py` entfernt. Dieses Patch-Skript enthielt:

```python
def _is_ultrawide(self, w: int, h: int) -> bool:
    """True wenn Quelle breiter als 16:9 ist (z.B. 32:9 OBS-Split-Recording)."""
    return h > 0 and (w / h) > 2.0
```

Diese Methode steuerte den bedingten Filter-Pfad. Beim Refactoring (von `-vf` → `-filter_complex`, von `_extract_segment`-intern → `_build_filter_complex`-extern) wurde die Ultrawide-Prüfung **nicht in den Hauptcode übertragen**. Das Entfernen der Patch-Skripte als "obsolet" erfolgte, bevor die Logik vollständig integriert war.

---

## 8. Vorgeschlagene Fixes (NUR Beschreibung — nicht implementiert)

### Fix A — Minimaler Fix: `_is_ultrawide()`-Check einbauen

In `_build_filter_complex()` prüfen, ob die Source wirklich ultrawide ist, bevor der Split-Filter angewendet wird. Für 16:9-Sources (`src_w / src_h ≤ 2.0`) direkt skalieren ohne Split/Crop:

```python
if not (src_h > 0 and src_w / src_h > 2.0):
    return "[0:v]scale=1920:1080[out]", "[out]"
```

Für 32:9-Sources die hardcodierten 1920-Werte durch `src_w // 2` ersetzen.

**Vorteil:** Klein, verhindert den Crash.  
**Nachteil:** Die grundlegende Architektur-Lücke (crop_window ignoriert) bleibt.

---

### Fix B — Robuster Fix: `crop_window` aus `FramingInstruction` nutzen

`reframing_core.py:56–62` speichert bereits normalisierte Koordinaten (0.0–1.0). Diese mit `src_w`/`src_h` multiplizieren statt hardcodierter Werte:

```python
# In _build_filter_complex():
cw = instr.crop_window  # z.B. {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0}
gp_x = int(cw["x"] * src_w)          # 0.5 * 1920 = 960  (korrekt für 1920px)
gp_w = int(cw["width"] * src_w)       # 0.5 * 1920 = 960
# → crop={gp_w}:{src_h}:{gp_x}:0
```

**Vorteil:** Auflösungsunabhängig; ReframingCore und FinalRenderDriver arbeiten korrekt zusammen.  
**Nachteil:** Die PiP-Facecam-Koordinaten kommen nicht aus crop_window (nur primäres Fenster gespeichert) — muss separat gelöst werden.

---

### Fix C — `app.py:745`: `source_aspect_ratio` dynamisch ermitteln

Statt hardcoded `"32:9"` die tatsächliche Videodimension per `ffprobe` lesen und daraus das Seitenverhältnis ableiten — bevor `ReframingCore().build_plan()` aufgerufen wird.
