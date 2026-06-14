# Music Apply Recipe

Quelle: aktueller dirty Stand von `scripts/controlled_music_preview_render.py` bei HEAD `e2d5259b783cd05281962337a4b32eb5af7b15e2`.

Diese Datei sichert nur das bewahrte Vorschau-Rezept als Produktionsreferenz. Sie ist kein aktiver Codepfad.

## Konstanten

```text
TARGET_MUSIC_ST_P95_LUFS = -17.0
TARGET_MUSIC_LUFS = -20.0
TARGET_SPEECHBAND_LUFS = -26.0

MUSIC_BED_GAIN_DB = -34.0
MUSIC_BED_GAIN_MIN_DB = -60.0
MUSIC_BED_GAIN_MAX_DB = 12.0

PER_TRACK_NORMALIZATION_GAIN_RANGE_DB = [-4.0, 4.0]
PER_TRACK_LUFS_NORMALIZATION_GAIN_RANGE_DB = [-4.0, 4.0]

DYNAUDNORM_FILTER = "dynaudnorm=f=250:g=31:m=8:p=0.9"
  f = 250
  g = 31
  m = 8
  p = 0.9

MUSIC_CONST_COMPRESSOR_FILTER = "acompressor=threshold=0.05:ratio=6:attack=20:release=250:makeup=8"
  threshold = 0.05
  ratio = 6
  attack = 20
  release = 250
  makeup = 8

SC_THRESHOLD = 0.03
SC_RATIO = 3
SC_ATTACK = 150
SC_RELEASE = 700

MUSIC_PEAK_LIMITER_ENABLED = True
MUSIC_PEAK_LIMITER_CEILING_DB = -37.0
MUSIC_PEAK_LIMITER_INTERNAL_LIMIT_DB = -24.0
MUSIC_PEAK_LIMITER_ATTACK_MS = 5
MUSIC_PEAK_LIMITER_RELEASE_MS = 80

Peak-Limiter-Shift:
  limiter_shift_db = MUSIC_PEAK_LIMITER_INTERNAL_LIMIT_DB - MUSIC_PEAK_LIMITER_CEILING_DB
  limiter_shift_db = -24.0 - (-37.0) = 13.0
  limiter_limit_linear = 10 ** (-24.0 / 20.0) = 0.06309573
```

## Messmethode

Integrated LUFS:

```bash
ffmpeg -hide_banner -nostats -i <music_file> \
  -filter:a "loudnorm=I=-20.0:TP=-1.5:LRA=11:print_format=json" \
  -f null <null>
```

Auswertung:

```text
integrated_lufs = loudnorm JSON input_i
lra = loudnorm JSON input_lra
```

Speechband LUFS:

```bash
ffmpeg -hide_banner -nostats -i <music_file> \
  -filter:a "highpass=f=300,lowpass=f=5000,loudnorm=I=-20.0:TP=-1.5:LRA=11:print_format=json" \
  -f null <null>
```

Short-term p95 LUFS:

```bash
ffmpeg -hide_banner -loglevel verbose -nostats -i <music_file> \
  -filter:a "ebur128=framelog=verbose" \
  -f null <null>
```

Auswertung:

```text
Regex je ebur128-Zeile:
  t:<time> TARGET:<target> LUFS M:<momentary> S:<shortterm>

Samples mit shortterm_lufs <= -100.0 werden verworfen.
st_p95_lufs = 95. Perzentil der shortterm_lufs-Samples.
Index im dirty Skript:
  index = int(round(0.95 * (len(ordered) - 1)))
```

Per-Song Normalisierung:

```text
raw_st_p95_gain_db = TARGET_MUSIC_ST_P95_LUFS - measured_st_p95_lufs
final_normalization_gain_db = raw_st_p95_gain_db
allowed range = [-4.0, 4.0]
```

## Filtergraph-Reihenfolge

Ziel-Reihenfolge:

```text
1. pro Song: Source-Trim -> PTS reset -> st_p95-Normalisierungs-Gain -> Fade-In/Fade-Out -> Delay/Placement
2. Concat/Crossfade bzw. Timeline-Bed-Aufbau zu [musicbed]
3. dynaudnorm
4. acompressor
5. konstanter Bett-Gain
6. sidechaincompress gegen saubere Stimmspur
7. Peak-Limiter mit +13 dB / alimiter / -13 dB
8. amix mit Original-/Master-Audio
```

Kopierbare Referenz mit Platzhaltern:

```text
[1:a]atrim=start=<track_1_start>:end=<track_1_end>,asetpts=PTS-STARTPTS,volume=<track_1_st_p95_gain_db>dB,afade=t=in:st=0:d=<fade_in>,afade=t=out:st=<fade_out_start>:d=<fade_out>,adelay=<delay_1_ms>:all=1[musicSegment1];
[2:a]atrim=start=<track_2_start>:end=<track_2_end>,asetpts=PTS-STARTPTS,volume=<track_2_st_p95_gain_db>dB,afade=t=in:st=0:d=<fade_in>,afade=t=out:st=<fade_out_start>:d=<fade_out>,adelay=<delay_2_ms>:all=1[musicSegment2];
[musicSegment1][musicSegment2]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[musicbed];
[musicbed]dynaudnorm=f=250:g=31:m=8:p=0.9,acompressor=threshold=0.05:ratio=6:attack=20:release=250:makeup=8[music_const];
[music_const]volume=-34.0dB[music_bed];
[music_bed][voice_clean]sidechaincompress=threshold=0.03:ratio=3:attack=150:release=700[music_ducked_prelimit];
[music_ducked_prelimit]volume=13.0dB,alimiter=limit=0.06309573:attack=5:release=80:level=0,volume=-13.0dB[music_ducked];
[program_audio][music_ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]
```

Hinweis zur Vorschau-Implementierung:

```text
Der dirty Preview-Code baut den Bed aktuell mit segmentierten Labels [musicSegmentN] und
amix=inputs=N:duration=longest:dropout_transition=0:normalize=0[musicbed].
Einzelne Segmente erhalten atrim/asetpts/volume/afade/adelay.
```

Dirty-Code-Entsprechung der robusten Leveling-Stufe:

```text
[musicbed]dynaudnorm=f=250:g=31:m=8:p=0.9,acompressor=threshold=0.05:ratio=6:attack=20:release=250:makeup=8[music_const];
[music_const]volume=-34.0dB[music_bed];
[music_bed][0:a]sidechaincompress=threshold=0.03:ratio=3:attack=150:release=700[music_ducked_prelimit];
[music_ducked_prelimit]volume=13.0dB,alimiter=limit=0.06309573:attack=5:release=80:level=0,volume=-13.0dB[music_ducked];
[0:a][music_ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]
```

Produktionshinweis:

```text
In Produktion darf der sidechain nicht auf dem Roh-Fullmix [0:a] ducking-triggern.
Der sidechain duckt auf die sauberen Stimmspuren ali+friend, z.B. [voice_clean].
Der finale amix mischt danach [program_audio] + [music_ducked].
```

