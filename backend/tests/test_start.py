import pytest

from backend.start import get_port


def test_get_port_defaults_to_8000(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORT", raising=False)

    assert get_port() == 8000


def test_get_port_reads_platform_port(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PORT", "10000")

    assert get_port() == 10000


@pytest.mark.parametrize("value", ["invalid", "0", "65536"])
def test_get_port_rejects_invalid_values(
    monkeypatch: pytest.MonkeyPatch,
    value: str,
) -> None:
    monkeypatch.setenv("PORT", value)

    with pytest.raises(RuntimeError, match="PORT must"):
        get_port()
