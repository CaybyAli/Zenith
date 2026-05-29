
import json
from pathlib import Path
from types import SimpleNamespace

from core.caption_ass_builder import CaptionASSBuilder, CaptionGroup
from core.shorts_render_driver import ShortsRenderDriver, _is_repetitive_caption_result
from core.shorts_transcript_caption_builder import build_sane_caption_words_from_transcript
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord
from pipeline_runner import _write_export_job_json


def _word(text, start, end, *, speaker="unknown", audio_track="mic"):
    return TranscriptWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=0.9,
        speaker=speaker,
        audio_track=audio_track,
    )


def test_p5_g5_caption_words_keep_speaker_and_audio_track():
    transcript = TranscriptResult(
        source_path="raw.mp4",
        language="de",
        engine="whisperx",
        full_text="ich komme nice save",
        segments=[
            TranscriptSegment(
                start_seconds=10.0,
                end_seconds=11.0,
                text="ich komme",
                speaker="owner",
                audio_track="mic",
                words=[
                    TranscriptWord(10.0, 10.4, "ich", 0.9),
                    TranscriptWord(10.4, 10.8, "komme", 0.9),
                ],
            ),
            TranscriptSegment(
                start_seconds=11.0,
                end_seconds=12.0,
                text="nice save",
                speaker="friend",
                audio_track="discord",
                words=[
                    TranscriptWord(11.0, 11.4, "nice", 0.9),
                    TranscriptWord(11.4, 11.8, "save", 0.9),
                ],
            ),
        ],
    )

    result = build_sane_caption_words_from_transcript(transcript, 10.0, 12.0)

    assert [word.audio_track for word in result.words] == ["mic", "mic", "discord", "discord"]
    assert [word.speaker for word in result.words] == ["owner", "owner", "friend", "friend"]


def test_p5_g5_ass_uses_green_for_owner_and_yellow_for_friend(tmp_path):
    out = tmp_path / "captions.ass"
    CaptionASSBuilder().generate_ass_file(
        caption_groups=[
            CaptionGroup(
                words=[
                    _word("ich", 0.0, 0.3, speaker="owner", audio_track="mic"),
                    _word("save", 0.3, 0.6, speaker="friend", audio_track="discord"),
                ]
            )
        ],
        output_path=str(out),
    )

    text = out.read_text(encoding="utf-8-sig")

    assert "&H0000FF00&" in text
    assert "&H0000FFFF&" in text


def test_p5_g5_ass_owner_has_priority_when_words_overlap():
    groups = CaptionASSBuilder().build_groups(
        [
            CaptionGroup(
                words=[
                    _word("friend", 0.0, 0.4, speaker="friend", audio_track="discord"),
                    _word("owner", 0.0, 0.4, speaker="owner", audio_track="mic"),
                ]
            )
        ]
    )

    flat = [word.text for group in groups for word in group]
    assert flat[:2] == ["owner", "friend"]


def test_p5_g5_repetitive_fake_caption_result_is_rejected(tmp_path):
    transcript = TranscriptResult(
        source_path="raw.mp4",
        language="de",
        engine="whisperx",
        full_text="cmon " * 12,
        segments=[
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=10.0,
                text="cmon " * 12,
                speaker="owner",
                audio_track="mic",
                words=[
                    TranscriptWord(float(index) * 0.4, float(index) * 0.4 + 0.2, "c'mon,", 0.9)
                    for index in range(12)
                ],
            )
        ],
    )

    clip = SimpleNamespace(
        source_start_time=0.0,
        source_end_time=10.0,
    )
    result = build_sane_caption_words_from_transcript(transcript, 0.0, 10.0)
    assert _is_repetitive_caption_result(result) is True

    output_path = tmp_path / "short.mp4"
    caption_filter = ShortsRenderDriver()._caption_filter_for_render(
        clip=clip,
        output_path=str(output_path),
        add_captions=True,
        transcript=transcript,
    )

    assert caption_filter == ""
    audit = json.loads(output_path.with_suffix(".caption_audit.json").read_text(encoding="utf-8"))
    assert audit["rejected_reason"] == "repetitive_caption_words"


def test_p5_g5_export_job_json_writes_transcript_sidecars(tmp_path):
    segments = [
        TranscriptSegment(
            start_seconds=0.0,
            end_seconds=1.0,
            text="hallo",
            speaker="owner",
            audio_track="mic",
            words=[
                TranscriptWord(
                    0.0,
                    0.5,
                    "hallo",
                    0.9,
                    speaker="owner",
                    audio_track="mic",
                )
            ],
        ).to_dict()
    ]

    class FakeJob:
        job_id = "job_caption_sidecar"

        def to_dict(self):
            return {
                "job_id": self.job_id,
                "status": "approval_pending",
                "transcription_engine": "whisperx",
                "transcript_text": "hallo",
                "transcript_segments": segments,
                "transcript_report": {
                    "engine": "whisperx",
                    "segments": segments,
                    "word_count": 1,
                },
            }

    job_json_path = _write_export_job_json(FakeJob(), tmp_path)
    payload = json.loads(job_json_path.read_text(encoding="utf-8"))

    assert payload["transcript_segments_path"]
    assert payload["transcript_report_path"]
    assert Path(payload["transcript_segments_path"]).exists()
    assert Path(payload["transcript_report_path"]).exists()

    sidecar = json.loads(Path(payload["transcript_segments_path"]).read_text(encoding="utf-8"))
    assert sidecar["count"] == 1
    assert sidecar["segments"][0]["speaker"] == "owner"
    assert sidecar["segments"][0]["audio_track"] == "mic"
