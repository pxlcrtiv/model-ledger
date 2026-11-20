"""Tests for the record-rendering module — one format spec, two adapters."""
import json
from pathlib import Path

from model_ledger.chain import ModelRecord
from model_ledger.formatter import fmt_record, to_json_spec

FIXTURE = Path(__file__).parent / "golden_render_fixture.json"


def _model_record(data: dict) -> ModelRecord:
    return ModelRecord(
        owner=data["owner"],
        manifest_hash=data["manifestHash"],
        repo_id=data["repoId"],
        metadata_uri=data["metadataUri"],
        registered_at=data["registeredAt"],
        updated_at=data["updatedAt"],
        manifest_version=data["manifestVersion"],
    )


def test_fmt_record_golden_fixture():
    """Python adapter: ModelRecord in -> golden text out, same fixture the
    web adapter is tested against (cli/tests/test_web_render.py)."""
    for case in json.loads(FIXTURE.read_text())["cases"]:
        assert fmt_record(_model_record(case["record"])) == case["expected"], case["name"]


def test_to_json_spec_golden():
    """The exported spec is the web viewer's source of truth: exact keys,
    order, widths, value types, and the empty-metadataUri dash rule."""
    assert to_json_spec() == [
        {"key": "repoId", "width": 17, "type": "string"},
        {"key": "owner", "width": 17, "type": "string"},
        {"key": "manifestHash", "width": 17, "type": "string"},
        {"key": "metadataUri", "width": 17, "type": "string", "empty": "-"},
        {"key": "registeredAt", "width": 17, "type": "timestamp"},
        {"key": "updatedAt", "width": 17, "type": "timestamp"},
        {"key": "manifestVersion", "width": 17, "type": "string"},
    ]
