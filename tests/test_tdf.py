import tempfile
import os
from datetime import datetime, timezone

from timepoint_tdf import (
    TDFRecord,
    TDFProvenance,
    from_clockchain,
    from_flash,
    from_pro,
    write_tdf_jsonl,
    read_tdf_jsonl,
)


def _sample_timestamp():
    return datetime(2024, 3, 15, 14, 0, 0, tzinfo=timezone.utc)


class TestTDFRecord:
    def test_creation_and_hash(self):
        record = TDFRecord(
            id="test-id-001",
            source="flash",
            timestamp=_sample_timestamp(),
            provenance=TDFProvenance(generator="timepoint-flash"),
            payload={"key": "value", "number": 42},
        )
        assert record.id == "test-id-001"
        assert record.version == "1.0.0"
        assert record.source == "flash"
        assert record.tdf_hash != ""
        assert len(record.tdf_hash) == 64  # SHA-256 hex digest

    def test_hash_changes_when_payload_changes(self):
        common = dict(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            provenance=TDFProvenance(generator="test"),
        )
        r1 = TDFRecord(payload={"a": 1}, **common)
        r2 = TDFRecord(payload={"a": 2}, **common)
        assert r1.tdf_hash != r2.tdf_hash

    def test_hash_stable_for_same_payload(self):
        common = dict(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            provenance=TDFProvenance(generator="test"),
        )
        r1 = TDFRecord(payload={"x": 1, "y": 2}, **common)
        r2 = TDFRecord(payload={"y": 2, "x": 1}, **common)
        assert r1.tdf_hash == r2.tdf_hash


class TestFromClockchain:
    def test_basic_transform(self):
        node = {
            "path": "/2024/march/15/1400/united-states/test-event",
            "id": "cc-node-uuid",
            "created_at": "2024-03-15T14:00:00+00:00",
            "flash_timepoint_id": "flash-uuid-123",
            "confidence": 0.95,
            "title": "Test Event",
            "body": "Something happened",
        }
        record = from_clockchain(node)
        assert record.id == "/2024/march/15/1400/united-states/test-event"
        assert record.source == "clockchain"
        assert record.provenance.generator == "timepoint-clockchain"
        assert record.provenance.flash_id == "flash-uuid-123"
        assert record.provenance.confidence == 0.95
        assert "title" in record.payload
        assert "body" in record.payload
        assert "path" not in record.payload
        assert "created_at" not in record.payload

    def test_falls_back_to_id_when_no_path(self):
        node = {
            "id": "cc-fallback-id",
            "created_at": "2024-03-15T14:00:00+00:00",
            "title": "Fallback",
        }
        record = from_clockchain(node)
        assert record.id == "cc-fallback-id"


class TestFromFlash:
    def test_basic_transform(self):
        timepoint = {
            "id": "flash-uuid-456",
            "created_at": "2024-03-15T14:00:00+00:00",
            "query": "Test query",
            "slug": "test-query-abc",
            "year": 1941,
            "month": 12,
            "day": 15,
            "season": "winter",
            "time_of_day": "afternoon",
            "era": "World War II",
            "location": "Bletchley Park",
            "scene_data": {"location": "park"},
            "character_data": [{"name": "Alice"}],
            "dialog": ["Hello"],
            "grounding_data": {"verified": True},
            "moment_data": {"tension": "high"},
            "metadata": {"source_file": "test.mp4"},
            "internal_field": "should_be_excluded",
        }
        record = from_flash(timepoint)
        assert record.id == "flash-uuid-456"
        assert record.source == "flash"
        assert record.provenance.generator == "timepoint-flash"
        assert record.provenance.flash_id == "flash-uuid-456"
        expected_keys = {
            "query", "slug", "year", "month", "day", "season",
            "time_of_day", "era", "location", "scene_data",
            "character_data", "dialog", "grounding_data",
            "moment_data", "metadata",
        }
        assert set(record.payload.keys()) == expected_keys
        assert record.payload["year"] == 1941
        assert record.payload["location"] == "Bletchley Park"
        assert record.payload["grounding_data"] == {"verified": True}
        assert record.payload["moment_data"] == {"tension": "high"}
        assert "internal_field" not in record.payload

    def test_missing_optional_fields_default_to_none(self):
        timepoint = {
            "id": "flash-uuid-minimal",
            "created_at": "2024-03-15T14:00:00+00:00",
        }
        record = from_flash(timepoint)
        assert record.payload["query"] is None
        assert record.payload["grounding_data"] is None
        assert record.payload["moment_data"] is None


class TestFromPro:
    def test_basic_transform(self):
        run_data = {
            "run_id": "pro-run-789",
            "created_at": "2024-03-15T14:00:00+00:00",
            "entities": [{"name": "Alice", "type": "person"}],
            "dialogs": [{"speaker": "Alice", "text": "Hi"}],
            "causal_edges": [{"from": "A", "to": "B"}],
            "metadata": {"model": "gpt-4"},
        }
        record = from_pro(run_data)
        assert record.id == "pro-run-789"
        assert record.source == "pro"
        assert record.provenance.generator == "timepoint-pro"
        assert record.provenance.run_id == "pro-run-789"
        assert "entities" in record.payload
        assert "dialogs" in record.payload
        assert "causal_edges" in record.payload
        assert "metadata" in record.payload


class TestJSONLRoundTrip:
    def test_write_and_read(self):
        records = [
            TDFRecord(
                id=f"record-{i}",
                source="flash",
                timestamp=_sample_timestamp(),
                provenance=TDFProvenance(generator="test", flash_id=f"flash-{i}"),
                payload={"index": i, "data": f"item-{i}"},
            )
            for i in range(3)
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            tmp_path = f.name

        try:
            write_tdf_jsonl(records, tmp_path)
            loaded = read_tdf_jsonl(tmp_path)
            assert len(loaded) == 3
            for orig, loaded_rec in zip(records, loaded):
                assert orig.id == loaded_rec.id
                assert orig.tdf_hash == loaded_rec.tdf_hash
                assert orig.payload == loaded_rec.payload
                assert orig.provenance == loaded_rec.provenance
        finally:
            os.unlink(tmp_path)
