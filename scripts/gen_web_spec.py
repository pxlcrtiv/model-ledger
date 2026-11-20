#!/usr/bin/env python3
"""Regenerate the format-spec block embedded in web/index.html.

The block is the export of model_ledger.formatter.to_json_spec(). After
changing FORMAT_SPEC, run this script so the web viewer inherits the change;
cli/tests/test_web_render.py fails if the embedded block drifts from the
export. Mirrors scripts/gen_golden.py (golden manifest hashes).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    sys.path.insert(0, str(ROOT / "cli"))
    from model_ledger.formatter import to_json_spec

    html_path = ROOT / "web" / "index.html"
    html = html_path.read_text()
    block = json.dumps(to_json_spec(), indent=2)
    pattern = re.compile(r'(<script type="application/json" id="format-spec">)[\s\S]*?(</script>)')
    new_html, n = pattern.subn(lambda m: m.group(1) + "\n" + block + "\n" + m.group(2), html)
    if n != 1:
        sys.exit("expected exactly one embedded format-spec block in web/index.html")
    html_path.write_text(new_html)
    print(f"web/index.html format-spec block regenerated ({len(to_json_spec())} fields)")


if __name__ == "__main__":
    main()
