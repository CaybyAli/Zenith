
from types import SimpleNamespace

from core.final_render_driver import FinalRenderDriver
from core.focus_switch_engine import FocusSwitchEngine


def test_p5_g4_gameplay_majority_renders_gameplay_crop_even_with_lower_confidence():
    driver = FinalRenderDriver()
    segment = SimpleNamespace(
        segment_id="seg_gameplay_majority",
        start_time=0.0,
        end_time=10.0,
    )
    job = SimpleNamespace(
        focus_decisions=[
            {
                "timestamp": 1.0,
                "focus_target": "gameplay",
                "confidence": 0.55,
                "reasoning": "gameplay_majority_1",
            },
            {
                "timestamp": 2.0,
                "focus_target": "gameplay",
                "confidence": 0.55,
                "reasoning": "gameplay_majority_2",
            },
            {
                "timestamp": 3.0,
                "focus_target": "gameplay",
                "confidence": 0.55,
                "reasoning": "gameplay_majority_3",
            },
            {
                "timestamp": 5.0,
                "focus_target": "facecam",
                "confidence": 0.95,
                "reasoning": "single_high_confidence_facecam",
            },
        ]
    )

    policy = driver._resolve_focus_render_policy(segment=segment, job=job)

    assert policy["focus_target"] == "gameplay"
    assert policy["layout_kind"] == "gameplay_crop"
    assert policy["selection_rule"] == "segment_focus_majority_gameplay"
    assert policy["segment_focus_counts"]["gameplay"] == 3
    assert policy["segment_focus_counts"]["facecam"] == 1


def test_p5_g4_facecam_majority_renders_facecam_emphasis():
    driver = FinalRenderDriver()
    segment = SimpleNamespace(
        segment_id="seg_facecam_majority",
        start_time=0.0,
        end_time=10.0,
    )
    job = SimpleNamespace(
        focus_decisions=[
            {"timestamp": 1.0, "focus_target": "facecam", "confidence": 0.5},
            {"timestamp": 2.0, "focus_target": "facecam", "confidence": 0.5},
            {"timestamp": 3.0, "focus_target": "gameplay", "confidence": 0.95},
        ]
    )

    policy = driver._resolve_focus_render_policy(segment=segment, job=job)

    assert policy["focus_target"] == "facecam"
    assert policy["layout_kind"] == "facecam_emphasis"
    assert policy["selection_rule"] == "segment_focus_majority_facecam"


def test_p5_g4_focus_switch_engine_consumes_gaming_pairs_style_dna():
    engine = FocusSwitchEngine()
    report = engine.style_dna_consumption_report()

    assert report["loaded"] is True
    assert report["content_type"] == "gaming_pairs"
    assert report["path"].replace("\\", "/").endswith("style_dna/ali/gaming_pairs_style_dna.json")
    assert report["normal_voice_gameplay_confidence_before"] == 0.55
    assert report["normal_voice_gameplay_confidence_after"] > 0.55
    assert "confidence 0.55->" in report["changed_decision"]
