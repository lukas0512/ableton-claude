import platform

import pytest

torch = pytest.importorskip("torch")
from ableton_claude import ear


@pytest.mark.parametrize("machine,mps,expected", [("arm64", True, "mps"), ("arm64", False, "cpu"),
                                                  ("x86_64", True, "cpu"), ("x86_64", False, "cpu")])
def test_torch_device_uses_mps_only_on_apple_silicon(monkeypatch, machine, mps, expected):
    monkeypatch.delenv("ABLETON_CLAUDE_DEVICE", raising=False)
    monkeypatch.setattr(platform, "machine", lambda: machine)
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: mps)
    assert ear.torch_device() == expected


def test_torch_device_override(monkeypatch):
    monkeypatch.setenv("ABLETON_CLAUDE_DEVICE", "cpu")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(torch.backends.mps, "is_available", lambda: True)
    assert ear.torch_device() == "cpu"
