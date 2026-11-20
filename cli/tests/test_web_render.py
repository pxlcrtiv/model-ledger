"""Behavioural golden tests for the web adapter of the record format spec.

Executes web/render.js (the exact file the viewer loads) and the page's own
inline script under node against the shared golden fixture — record/spec in,
rendered text out — instead of grepping the HTML source for presentation rules.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from model_ledger.formatter import to_json_spec

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = Path(__file__).parent / "golden_render_fixture.json"
HARNESS = Path(__file__).parent / "web_render_harness.cjs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")


def _run_harness() -> dict[str, list[str]]:
    proc = subprocess.run(
        ["node", str(HARNESS), str(FIXTURE)],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=REPO_ROOT,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def _assert_golden(rendered: list[str]) -> None:
    cases = json.loads(FIXTURE.read_text())["cases"]
    assert len(rendered) == len(cases)
    for case, got in zip(cases, rendered):
        assert got == case["expected"], f"web renderer drifted on case {case['name']!r}"


def test_web_renderer_matches_golden_fixture():
    _assert_golden(_run_harness()["direct"])


def test_web_page_script_renders_golden_fixture():
    """The page's actual inline script (embedded-spec parse + fmtRecord
    wiring), executed with DOM stubs, renders the same golden text."""
    _assert_golden(_run_harness()["page"])


def test_embedded_spec_matches_exported_spec():
    """The spec embedded in web/index.html is exactly to_json_spec() —
    the anchor that keeps the static page in sync with the Python module."""
    html = (REPO_ROOT / "web" / "index.html").read_text()
    m = re.search(r'<script type="application/json" id="format-spec">(.*?)</script>', html, re.DOTALL)
    assert m, "web/index.html must embed the exported format spec"
    assert json.loads(m.group(1)) == to_json_spec()
