VIDEO: LoL
quelldauer_sekunden: 1017.833333

[TIMELINE-SCORE-POOLS] primary=32 reserve=67 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=610.698s floor=480.000s selected=480.330s primary_candidates=32 reserve_candidates=67 reserve_used=23 max_segments=61
keine [TIMELINE-DURATION-FLOOR-BLOCKED]/[TIMELINE-DURATION-FLOOR-OK]-Zeile im Pipeline-Output
[pipeline_runner] Done ? ok=1  skipped=0  failed=0

ffprobe_final:
duration=490.851758
codec_type=video
codec_name=h264
width=1920
height=1080
display_aspect_ratio=16:9

VIDEO: Minecraft
quelldauer_sekunden: 2670.070000

[TIMELINE-SCORE-POOLS] primary=37 reserve=316 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=934.524s floor=480.000s selected=492.500s primary_candidates=37 reserve_candidates=316 reserve_used=19 max_segments=93
keine [TIMELINE-DURATION-FLOOR-BLOCKED]/[TIMELINE-DURATION-FLOOR-OK]-Zeile im Pipeline-Output
[pipeline_runner] Done ? ok=1  skipped=0  failed=0

ffprobe_final:
duration=736.000438
codec_type=video
codec_name=h264
width=1920
height=1080
display_aspect_ratio=16:9

VIDEO: Fortnite
quelldauer_sekunden: 1820.816667

[TIMELINE-SCORE-POOLS] primary=38 reserve=227 threshold=0.45
[TIMELINE-DURATION-FLOOR] target=637.287s floor=480.000s selected=483.000s primary_candidates=38 reserve_candidates=227 reserve_used=10 max_segments=63
[TIMELINE-DURATION-FLOOR-BLOCKED] selected_after_guards=443.820s floor=480.000s primary=38 reserve=227 target=637.287s
[pipeline_runner] Done ? ok=0  skipped=0  failed=1

ffprobe_final:
kein MP4 erzeugt

| Video     | Quelldauer  | selected_after_guards | MP4 erzeugt | im 480-1200s-Fenster |
| LoL       | 1017.833333 | nicht geloggt         | ja           | ja                   |
| Minecraft | 2670.070000 | nicht geloggt         | ja           | ja                   |
| Fortnite  | 1820.816667 | 443.820s              | nein         | nein                 |
