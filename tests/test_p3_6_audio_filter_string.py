from types import SimpleNamespace

from core.audio_normalizer import AudioNormalizer, AudioNormalizationResult


def _measured():
    return {
        "input_i": -18.25,
        "input_lra": 7.75,
        "input_tp": -2.50,
        "input_thresh": -28.10,
    }


def test_pass2_filter_string_is_deterministic():
    """Gleiche measured-Werte → zweimal aufgerufen → identischer String."""
    normalizer = AudioNormalizer(target_i=-14.0, target_tp=-1.0)

    first = normalizer.build_pass2_filter(_measured())
    second = normalizer.build_pass2_filter(_measured())

    assert first == second
    assert "loudnorm=" in first
    assert "measured_I=-18.25" in first


def test_target_values_from_contract():
    """target_i und target_tp kommen aus contract, kein Hardcode."""
    contract = SimpleNamespace(target_lufs=-16.0, target_tp=-2.0)

    normalizer = AudioNormalizer.from_contract(contract)

    assert normalizer.target_i == -16.0
    assert normalizer.target_tp == -2.0


def test_skip_when_measured_empty():
    """build_result mit leerem measured → skipped=True, kein Crash."""
    normalizer = AudioNormalizer()

    result = normalizer.build_result({})

    assert result.skipped is True
    assert result.filter_string == ""
    assert result.warnings


def test_result_to_dict_is_serializable():
    """to_dict() gibt valides dict zurück, alle Felder vorhanden."""
    normalizer = AudioNormalizer()
    result = normalizer.build_result(_measured())

    payload = result.to_dict()

    assert isinstance(result, AudioNormalizationResult)
    assert set(payload) == {
        "input_i",
        "input_lra",
        "input_tp",
        "input_thresh",
        "target_i",
        "target_tp",
        "filter_string",
        "skipped",
        "warnings",
    }
    assert payload["skipped"] is False


def test_parse_pass1_output_extracts_json():
    """Ffmpeg stderr mit eingebettetem JSON-Block → korrekte Werte."""
    stderr = """
    ffmpeg noise before
    {
      "input_i": "-20.30",
      "input_tp": "-1.70",
      "input_lra": "5.60",
      "input_thresh": "-30.40",
      "output_i": "-14.00"
    }
    ffmpeg noise after
    """
    normalizer = AudioNormalizer()

    parsed = normalizer.parse_pass1_output(stderr)

    assert parsed == {
        "input_i": -20.30,
        "input_lra": 5.60,
        "input_tp": -1.70,
        "input_thresh": -30.40,
    }


def test_parse_pass1_output_no_json_returns_empty():
    """Keine JSON-Block in stderr → leeres dict, kein Crash."""
    normalizer = AudioNormalizer()

    assert normalizer.parse_pass1_output("no loudnorm json here") == {}
