# CORPUS TRUTH

## Pair Truth

`video_configs/pair_track_truth.json` ist Ground Truth.

## Harte Regeln

- Ali-Quelle niemals aus alter `track_mapping` ableiten.
- Ali-Quelle muss über `core.pair_track_truth_loader.get_ali_source` kommen.
- `ali_voice_reference.wav` ist kontaminiert und darf nicht als saubere Ali-Quelle genutzt werden.

## Bekannte Korpus-Wahrheit

- 20 Pairs
- Ali clean: 20
- Friend clean: 7
- Solos: 5
- Game clean: 12
