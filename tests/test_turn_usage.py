"""scripts/turn_usage.py (#322): the voice relay's monthly use, read from Cloudflare's answer."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("turn_usage", Path(__file__).parent.parent / "scripts" / "turn_usage.py")
turn_usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(turn_usage)


def answer(groups):
    return {"data": {"viewer": {"accounts": [{"callsTurnUsageAdaptiveGroups": groups}]}}, "errors": None}


def test_the_month_is_every_group_in_and_out():
    groups = [{"sum": {"egressBytes": 1000, "ingressBytes": 200}}, {"sum": {"egressBytes": 5, "ingressBytes": None}}]
    assert turn_usage.month_bytes(answer(groups)) == 1205
    assert turn_usage.month_bytes(answer([])) == 0


def test_an_error_is_not_read_as_no_use():
    with pytest.raises(RuntimeError):
        turn_usage.month_bytes({"data": None, "errors": [{"message": "not authorized"}]})
