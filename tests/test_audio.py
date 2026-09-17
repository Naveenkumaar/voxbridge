"""Mic capture: is_silent is pure and tested; recording is skipped without deps."""
import pytest

from app.audio import is_silent


def test_is_silent_on_empty_and_quiet():
    assert is_silent([])
    assert is_silent([0, 1, -2, 3, -1])            # tiny amplitudes → silent


def test_is_not_silent_on_loud_audio():
    assert not is_silent([2000, -3000, 2500, -2800])


def test_threshold_is_respected():
    samples = [600, -600, 600, -600]               # mean abs = 600
    assert is_silent(samples, threshold=1000)
    assert not is_silent(samples, threshold=100)


def test_record_wav_available_but_skipped_without_hardware():
    pytest.importorskip("sounddevice")             # skip if optional dep absent
    from app.audio import record_wav
    assert callable(record_wav)                    # don't actually open a mic in CI
