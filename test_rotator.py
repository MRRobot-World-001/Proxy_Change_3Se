"""
tests/test_rotator.py — Unit tests for tor_rotator helpers
"""
import sys
import os

# Stub out stem so tests work without Tor installed
import types

stem_stub = types.ModuleType("stem")
stem_stub.Signal = type("Signal", (), {"NEWNYM": "NEWNYM"})()
sys.modules["stem"] = stem_stub

stem_control = types.ModuleType("stem.control")
class FakeController:
    @classmethod
    def from_port(cls, **kw): return cls()
    def __enter__(self): return self
    def __exit__(self, *a): pass
    def authenticate(self, **kw): pass
    def set_conf(self, *a): pass
    def signal(self, *a): pass

stem_control.Controller = FakeController
sys.modules["stem.control"] = stem_control
sys.modules["stem.process"] = types.ModuleType("stem.process")

import tor_rotator


def test_countries_not_empty():
    assert len(tor_rotator.COUNTRIES) > 0


def test_status_initial():
    st = tor_rotator.status()
    assert "running" in st
    assert "interval" in st
    assert st["interval"] == 3


def test_rotate_interval():
    assert tor_rotator.ROTATE_INTERVAL == 3


def test_log_file_path():
    from pathlib import Path
    assert tor_rotator.LOG_FILE == Path("logs/ip.txt")


def test_countries_are_valid_iso():
    """All country codes should be 2 lowercase letters."""
    for cc in tor_rotator.COUNTRIES:
        assert len(cc) == 2
        assert cc.islower()
