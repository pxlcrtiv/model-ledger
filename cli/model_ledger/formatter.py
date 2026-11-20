"""Record rendering — one format spec, two adapters.

This module is the single source of truth for ModelRecord presentation.
The CLI text renderer (fmt_record) and the web viewer (web/render.js,
driven by the spec embedded in web/index.html) both render from FORMAT_SPEC,
so field order, label widths, timestamp style, and the empty-URI dash rule
change in exactly one place.
"""
from __future__ import annotations

import datetime as _dt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .chain import ModelRecord

# key: record field (camelCase, as in ModelRecord.to_dict / on-chain ABI)
# width: label column width (label is left-justified, never truncated)
# type: "string" or "timestamp" (unix seconds -> "%Y-%m-%d %H:%M:%S UTC")
# empty: replacement text when a string value is empty (optional)
FORMAT_SPEC: list[dict] = [
    {"key": "repoId", "width": 17, "type": "string"},
    {"key": "owner", "width": 17, "type": "string"},
    {"key": "manifestHash", "width": 17, "type": "string"},
    {"key": "metadataUri", "width": 17, "type": "string", "empty": "-"},
    {"key": "registeredAt", "width": 17, "type": "timestamp"},
    {"key": "updatedAt", "width": 17, "type": "timestamp"},
    {"key": "manifestVersion", "width": 17, "type": "string"},
]


def _render_value(entry: dict, value: str | int) -> str:
    if entry["type"] == "timestamp":
        return _dt.datetime.fromtimestamp(int(value), tz=_dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    text = str(value)
    return text if text else entry.get("empty", "")


def fmt_record(record: ModelRecord) -> str:
    """Render a ModelRecord as the CLI's indented label/value block."""
    values = record.to_dict()
    return "\n".join(
        "  " + entry["key"].ljust(entry["width"]) + _render_value(entry, values[entry["key"]])
        for entry in FORMAT_SPEC
    )


def to_json_spec() -> list[dict]:
    """Export the format spec as JSON-serialisable dicts for the web viewer."""
    return [dict(entry) for entry in FORMAT_SPEC]
