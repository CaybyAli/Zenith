from core.render_plan_builder import build_render_plan


def _base_job(**overrides):
    data = {
        "job_id": "job-render-plan-smoke",
        "input_file": "D:/media/source.mp4",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "render_readiness_status": "render_readiness_ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_can_start_render_pipeline": True,
        "render_readiness_blocking_count": 0,
        "render_readiness_blocking_reasons": [],
        "render_readiness_warnings": [],
        "render_readiness_guard_report": {
            "status": "render_readiness_ready",
            "ready_for_next_render_stage": True,
            "can_start_render_pipeline": True,
            "blocking_count": 0,
            "blocking_reasons": [],
            "warnings": [],
        },
        "review_timeline_plan_items": [
            {
                "item_id": "item-1",
                "segment_id": "seg-1",
                "start_seconds": 10.0,
                "end_seconds": 15.0,
                "duration_seconds": 5.0,
                "action": "keep",
                "transition_intent": "hard_cut",
                "protected": True,
                "review_required": False,
            },
            {
                "item_id": "item-2",
                "segment_id": "seg-2",
                "start_seconds": 30.0,
                "end_seconds": 34.0,
                "duration_seconds": 4.0,
                "action": "keep",
                "censor_sfx_required": True,
                "review_required": True,
            },
        ],
        "audio_tracks": [{"track_id": "mic"}, {"track_id": "game"}],
        "video_tracks": [{"track_id": "gameplay"}, {"track_id": "facecam"}],
    }
    data.update(overrides)
    return data


def _assert_dry_run_safety(report):
    assert report["dry_run_only"] is True
    assert report["can_execute_plan"] is False
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_write_media"] is False
    assert report["can_apply_timeline"] is False


def test_builder_blocks_when_render_readiness_guard_not_ready():
    report = build_render_plan(
        _base_job(
            render_readiness_status="render_readiness_blocked",
            render_readiness_guard_report={
                "status": "render_readiness_blocked",
                "ready_for_next_render_stage": False,
                "can_start_render_pipeline": False,
                "blocking_count": 1,
                "blocking_reasons": ["guard_blocked"],
                "warnings": [],
            },
        )
    )

    assert report["status"] == "render_plan_blocked"
    assert "render_plan_guard_not_ready" in report["blocking_reasons"]
    assert "render_plan_guard_next_stage_not_ready" in report["blocking_reasons"]
    assert "render_plan_guard_cannot_start_pipeline" in report["blocking_reasons"]
    assert report["ready_for_renderer_contract"] is False
    _assert_dry_run_safety(report)


def test_builder_blocks_when_can_start_render_pipeline_false():
    report = build_render_plan(
        _base_job(
            render_readiness_can_start_render_pipeline=False,
            render_readiness_guard_report={
                "status": "render_readiness_ready",
                "ready_for_next_render_stage": True,
                "can_start_render_pipeline": False,
                "blocking_count": 0,
                "blocking_reasons": [],
                "warnings": [],
            },
        )
    )

    assert report["status"] == "render_plan_blocked"
    assert "render_plan_guard_cannot_start_pipeline" in report["blocking_reasons"]
    _assert_dry_run_safety(report)


def test_builder_blocks_when_timeline_items_missing():
    report = build_render_plan(_base_job(review_timeline_plan_items=[]))

    assert report["status"] == "render_plan_blocked"
    assert "review_timeline_items_missing" in report["blocking_reasons"]
    assert "render_plan_no_timeline_items" in report["blocking_reasons"]
    assert report["total_segments"] == 0
    _assert_dry_run_safety(report)


def test_builder_creates_segments_and_continuous_output_times():
    report = build_render_plan(_base_job())

    assert report["status"] == "render_plan_ready_with_warnings"
    assert report["ready_for_renderer_contract"] is True
    assert report["total_segments"] == 2
    assert report["total_duration_seconds"] == 9.0
    assert report["estimated_output_duration_seconds"] == 9.0

    first, second = report["segments"]
    assert first["source_start_seconds"] == 10.0
    assert first["source_end_seconds"] == 15.0
    assert first["output_start_seconds"] == 0.0
    assert first["output_end_seconds"] == 5.0
    assert first["duration_seconds"] == 5.0

    assert second["source_start_seconds"] == 30.0
    assert second["source_end_seconds"] == 34.0
    assert second["output_start_seconds"] == 5.0
    assert second["output_end_seconds"] == 9.0
    assert second["duration_seconds"] == 4.0
    _assert_dry_run_safety(report)


def test_builder_blocks_invalid_timing():
    report = build_render_plan(
        _base_job(
            review_timeline_plan_items=[
                {
                    "item_id": "bad",
                    "start_seconds": 10.0,
                    "end_seconds": 9.0,
                    "duration_seconds": -1.0,
                }
            ]
        )
    )

    assert report["status"] == "render_plan_blocked"
    assert any("render_plan_invalid_timing" in item for item in report["blocking_reasons"])
    assert report["segments"][0]["blocking_reasons"]
    _assert_dry_run_safety(report)


def test_builder_plans_sources_without_opening_media():
    report = build_render_plan(_base_job())

    source = report["sources"][0]
    assert source["source_id"] == "source_main"
    assert source["path_hint"] == "D:/media/source.mp4"
    assert source["available"] is True
    assert source["metadata"]["path_hint_only"] is True
    assert source["metadata"]["file_not_checked"] is True
    assert source["metadata"]["media_not_opened"] is True
    assert len(report["sources"]) >= 5
    _assert_dry_run_safety(report)


def test_missing_source_hint_is_warning_not_media_access():
    report = build_render_plan(
        _base_job(
            input_file=None,
            source_file=None,
            media_path=None,
            raw_video_path=None,
            video_path=None,
            file_path=None,
        )
    )

    assert report["status"] == "render_plan_ready_with_warnings"
    assert "render_plan_missing_source_hint" in report["warnings"]
    assert "render_plan_required_source_path_hint_missing" in report["warnings"]
    assert report["sources"][0]["available"] is False
    _assert_dry_run_safety(report)


def test_output_target_and_operation_intents_are_planned_only():
    report = build_render_plan(_base_job())

    target = report["output_targets"][0]
    assert target["container"] == "mp4"
    assert target["video_codec_intent"] == "h264"
    assert target["audio_codec_intent"] == "aac"
    assert target["resolution_intent"] == "1080p60"
    assert target["audio_lufs_intent"] == -14.0
    assert target["filename_hint"].endswith(".mp4")

    intent_types = {item["intent_type"] for item in report["operation_intents"]}
    assert "trim_intent" in intent_types
    assert "concat_intent" in intent_types
    assert "transition_intent" in intent_types
    assert "censor_sfx_intent" in intent_types
    assert "output_encode_intent" in intent_types

    for intent in report["operation_intents"]:
        assert intent["can_execute_now"] is False
        assert intent["requires_later_renderer"] is True
        text = str(intent).lower()
        assert "raw_command" not in text
        assert "shell_command" not in text
        assert "command_line" not in text
        assert "ffmpeg_command" not in text
        assert "executable_command" not in text
        assert "argv" not in text

    _assert_dry_run_safety(report)
