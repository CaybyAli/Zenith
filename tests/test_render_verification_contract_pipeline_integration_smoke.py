from __future__ import annotations

from pathlib import Path


def test_pipeline_imports_render_verification_runner_after_output_format_runner():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    output_import = "from core.output_format_handler_runner import run_output_format_handler"
    verification_import = (
        "from core.render_verification_contract_runner import "
        "run_render_verification_contract"
    )

    assert output_import in text
    assert verification_import in text
    assert text.index(output_import) < text.index(verification_import)


def test_pipeline_runs_render_verification_contract_after_output_format_handler():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    output_call = "output_format_report = run_output_format_handler(job)"
    verification_call = "render_verification_report = run_render_verification_contract(job)"

    assert output_call in text
    assert verification_call in text
    assert text.index(output_call) < text.index(verification_call)


def test_pipeline_has_2b_56_safety_metadata_and_checkpoint():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert 'phase="2B-56"' in text
    assert 'action="run_render_verification_contract"' in text
    assert 'step_name="render_verification_contract_done"' in text
    assert '"render_verification_contract_only": True' in text
    assert '"probe_plan_only": True' in text
    assert '"no_" "ff" "probe_execution_in_2b_56": True' in text
    assert '"no_project_" "output_probe_in_2b_56": True' in text
    assert '"no_user_media_" "input_in_2b_56": True' in text
    assert '"no_project_" "output_write_in_2b_56": True' in text
    assert '"no_timeline_" "apply_in_2b_56": True' in text


def test_pipeline_never_enables_project_output_or_media_permissions_for_2b_56():
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    start = text.index('phase="2B-56"')
    end = text.index('except Exception as render_readiness_exc', start)
    block = text[start:end]

    assert '"can_verify_project_" "output": False' in block
    assert '"can_probe_media_files": False' in block
    assert '"can_render": False' in block
    assert '"can_write_media": False' in block
