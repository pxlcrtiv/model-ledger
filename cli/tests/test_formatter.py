"""Tests for RecordFormatter — single source of truth for record formatting."""

from model_ledger.formatter import RecordFormatter, fmt_record

EPOCH = 1700000000  # 2023-11-14 22:13:20 UTC


def test_fmt_record_exact_output():
    record = {
        "repoId": "test/repo",
        "owner": "0xabcdef1234567890",
        "manifestHash": "0x" + "ab" * 32,
        "metadataUri": "ipfs://QmTest",
        "registeredAt": EPOCH,
        "updatedAt": EPOCH,
        "manifestVersion": 1,
    }
    result = fmt_record(record)
    expected = (
        "  repoId           test/repo\n"
        "  owner            0xabcdef1234567890\n"
        "  manifestHash     0x" + "ab" * 32 + "\n"
        "  metadataUri      ipfs://QmTest\n"
        "  registeredAt     2023-11-14 22:13:20 UTC\n"
        "  updatedAt        2023-11-14 22:13:20 UTC\n"
        "  manifestVersion  1"
    )
    assert result == expected


def test_fmt_record_empty_metadata_uri_renders_dash():
    record = {
        "repoId": "test/repo",
        "owner": "0xabc",
        "manifestHash": "0xdef",
        "metadataUri": "",
        "registeredAt": EPOCH,
        "updatedAt": EPOCH,
        "manifestVersion": 1,
    }
    result = fmt_record(record)
    assert "metadataUri      -" in result
    assert "metadataUri      " not in result.replace("metadataUri      -", "")


def test_record_formatter_class_delegates():
    formatter = RecordFormatter()
    record = {
        "repoId": "r",
        "owner": "o",
        "manifestHash": "h",
        "metadataUri": "",
        "registeredAt": EPOCH,
        "updatedAt": EPOCH,
        "manifestVersion": 2,
    }
    assert formatter.format(record) == fmt_record(record)


def test_format_spec_export_shape():
    spec = RecordFormatter.to_json_spec()
    assert len(spec) == 7
    keys = [s["key"] for s in spec]
    assert keys == [
        "repoId",
        "owner",
        "manifestHash",
        "metadataUri",
        "registeredAt",
        "updatedAt",
        "manifestVersion",
    ]
    # Each entry has width and type
    for entry in spec:
        assert "key" in entry
        assert "width" in entry
        assert "type" in entry
        assert entry["width"] == 17
