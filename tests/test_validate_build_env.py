"""Tests for the narrow OpenCV packaging metadata exception."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "packaging"
    / "ai_client"
    / "validate_build_env.py"
)
SPEC = spec_from_file_location("fitroute_validate_build_env", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

ALLOWED_PIP_CHECK_EXCEPTION = VALIDATOR.ALLOWED_PIP_CHECK_EXCEPTION
classify_pip_check = VALIDATOR.classify_pip_check


EXPECTED_OPENCV = {"opencv-contrib-python": "5.0.0.93"}


def test_clean_pip_check_is_valid() -> None:
    allowed_count, unexpected = classify_pip_check(0, "", EXPECTED_OPENCV)

    assert allowed_count == 0
    assert unexpected == []


def test_exact_known_exception_with_expected_opencv_is_valid() -> None:
    allowed_count, unexpected = classify_pip_check(
        1,
        ALLOWED_PIP_CHECK_EXCEPTION,
        EXPECTED_OPENCV,
    )

    assert allowed_count == 1
    assert unexpected == []


def test_additional_conflict_is_rejected() -> None:
    output = ALLOWED_PIP_CHECK_EXCEPTION + "\nother 1.0 requires missing, not installed."

    allowed_count, unexpected = classify_pip_check(1, output, EXPECTED_OPENCV)

    assert allowed_count == 0
    assert len(unexpected) == 2


def test_known_exception_without_contrib_replacement_is_rejected() -> None:
    allowed_count, unexpected = classify_pip_check(
        1,
        ALLOWED_PIP_CHECK_EXCEPTION,
        {},
    )

    assert allowed_count == 0
    assert unexpected == [ALLOWED_PIP_CHECK_EXCEPTION]


def test_known_exception_with_duplicate_opencv_wheels_is_rejected() -> None:
    installed = {
        **EXPECTED_OPENCV,
        "opencv-python": "5.0.0.93",
    }

    allowed_count, unexpected = classify_pip_check(
        1,
        ALLOWED_PIP_CHECK_EXCEPTION,
        installed,
    )

    assert allowed_count == 0
    assert unexpected == [ALLOWED_PIP_CHECK_EXCEPTION]
