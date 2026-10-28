"""Verify web/index.html fmtRecord shares the same format spec as Python."""

from pathlib import Path

from model_ledger.formatter import FORMAT_SPEC

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_web_viewer_fmtrecord_order_matches_spec():
    html = (REPO_ROOT / "web" / "index.html").read_text()
    # Find the fmtRecord function body
    idx = html.find("function fmtRecord")
    assert idx >= 0, "fmtRecord function not found in web/index.html"
    body = html[idx:]

    # Labels must appear in the same order as FORMAT_SPEC
    pos = 0
    for label, _, _ in FORMAT_SPEC:
        found = body.find(label, pos)
        assert found >= pos, f"Label '{label}' missing or out of order in web viewer"
        pos = found + len(label)


def test_web_viewer_fmtrecord_uses_two_space_indent():
    html = (REPO_ROOT / "web" / "index.html").read_text()
    idx = html.find("function fmtRecord")
    assert idx >= 0
    body = html[idx:]

    for label, _, _ in FORMAT_SPEC:
        assert f"  {label}" in body, f"Expected 2-space indent for '{label}' in web viewer"


def test_web_viewer_fmtrecord_label_widths():
    """Each label in the JS template literal should be padded to 17 chars (matching Python)."""
    html = (REPO_ROOT / "web" / "index.html").read_text()
    idx = html.find("function fmtRecord")
    assert idx >= 0
    body = html[idx:]

    for label, width, _ in FORMAT_SPEC:
        # Look for the template literal containing this label
        pattern = f"`  {label:<{width}}"
        assert pattern in body, (
            f"Label '{label}' should be padded to width {width} in web viewer"
        )
