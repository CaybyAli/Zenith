# Phase 2 Whisper Evidence — P3-1

Status: CLOSED

HEAD at start:
30730d4

## Environment

Python:
C:\Python314\python.exe

faster-whisper:
1.2.1

Cached model:
models--Systran--faster-whisper-base

## Real Whisper probe

Fixture:
D:\Zenith\tests\fixtures\whisper_probe.wav

Test mode:
ZENITH_TRANSCRIPT_TEST_MODE was not set.

Offline mode:
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1

Model:
base

Device:
cpu

Compute type:
int8

## Raw manual probe result

Language:
en

Language probability:
0.9957541227340698

Audio duration:
4.273875 seconds

Model load seconds:
0.636

Inference seconds:
0.814

Segment count:
1

Transcript:
[0.00s -> 4.00s] The quick brown fox jumps over the lazy dog near the riverbank.

Full text:
The quick brown fox jumps over the lazy dog near the riverbank.

## P3-1 pytest proof

Command:
python -m pytest -m real_whisper tests/test_transcript_whisper_fixture_probe.py tests/test_p3_1_whisper_real.py -vv -s

Result:
tests/test_transcript_whisper_fixture_probe.py::test_whisper_transcribes_bundled_sapi_fixture PASSED
tests/test_p3_1_whisper_real.py::test_p3_1_whisper_probe_real_inference PASSED

Raw final line:
2 passed in 4.07s

## Marker safety proof

Command:
python -m pytest tests\test_p3_1_whisper_real.py -q

Raw final line:
1 deselected in 0.15s

## Conclusion

The Phase-2 protocol note about real Whisper evidence is closed.

This was a real faster-whisper inference run on whisper_probe.wav.
No stub, no mock, and no Zenith transcript test fallback were used.

The real_whisper marker is opt-in only and excluded from the default pytest run.
