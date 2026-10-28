"""Record formatting — single source of truth for both CLI and web viewer."""
from __future__ import annotations

import datetime as _dt
from collections.abc import Callable

FORMAT_SPEC: list[tuple[str, int, Callable[[str], str]]] = [
    ("repoId", 17, str),
    ("owner", 17, str),
    ("manifestHash", 17, str),
    ("metadataUri", 17, lambda x: x or "-"),
    ("registeredAt", 17, lambda x: _dt.datetime.fromtimestamp(x, tz=_dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")),
    ("updatedAt", 17, lambda x: _dt.datetime.fromtimestamp(x, tz=_dt.UTC).strftime("%Y-%m-%d %H:%M:%S UTC")),
    ("manifestVersion", 17, str),
]


def fmt_record(rec: dict) -> str:
    return "\n".join(
        f"  {label:<{width}}{fmt(rec.get(label, ''))}"
        for label, width, fmt in FORMAT_SPEC
    )


class RecordFormatter:
    """Encapsulates the record format spec for reuse by CLI and web viewer."""

    def format(self, record: dict) -> str:
        return fmt_record(record)

    @staticmethod
    def to_json_spec() -> list[dict]:
        """Export the format spec as JSON-serialisable dicts for the web viewer."""
        return [
            {
                "key": label,
                "width": width,
                "type": "timestamp" if "At" in label else "string",
            }
            for label, width, _ in FORMAT_SPEC
        ]
