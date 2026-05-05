import os
import tempfile
from pathlib import Path

from core.transcript_processor import TranscriptProcessor
from models.transcript_result import TranscriptResult, TranscriptSegment


def main() -> None:
    os.environ["ZENITH_TRANSCRIPT_TEST_MODE"] = "1"

    with tempfile.TemporaryDirectory() as temp_dir:
        test_video_path = Path(temp_dir) / "transcript_smoke_input.mp4"
        test_video_path.write_bytes(b"zenith transcript smoke placeholder")

        result = TranscriptProcessor().transcribe(str(test_video_path))

    assert isinstance(result, TranscriptResult)
    assert result.engine == "test-fallback"
    assert result.segments
    assert result.full_text.strip()

    previous_start = -1.0

    for segment in result.segments:
        assert isinstance(segment, TranscriptSegment)
        assert segment.start_seconds >= 0.0
        assert segment.end_seconds > segment.start_seconds
        assert segment.text.strip()
        assert segment.start_seconds >= previous_start
        previous_start = segment.start_seconds

    print("TRANSCRIPT SMOKE TEST PASSED")
    print(
        {
            "segments": len(result.segments),
            "engine": result.engine,
            "language": result.language,
            "full_text_chars": len(result.full_text),
        }
    )


if __name__ == "__main__":
    main()