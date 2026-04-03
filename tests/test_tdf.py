import tempfile
import os
from datetime import datetime, timezone

from timepoint_tdf import (
    TDFRecord,
    TDFProvenance,
    from_clockchain,
    from_flash,
    from_pro,
    from_proteus,
    SCHEMA_VERSIONS,
    infer_model_permissiveness,
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

    def test_new_provenance_fields_default(self):
        prov = TDFProvenance(generator="test")
        assert prov.text_model is None
        assert prov.image_model is None
        assert prov.model_provider is None
        assert prov.model_permissiveness is None
        assert prov.schema_version == "0.1"
        assert prov.generation_id is None

    def test_provenance_does_not_affect_hash(self):
        common = dict(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            payload={"same": "data"},
        )
        r1 = TDFRecord(provenance=TDFProvenance(generator="test"), **common)
        r2 = TDFRecord(
            provenance=TDFProvenance(
                generator="test",
                text_model="deepseek-r1",
                model_provider="openrouter",
                schema_version="0.2",
            ),
            **common,
        )
        assert r1.tdf_hash == r2.tdf_hash

    def test_entity_ids_default_empty(self):
        record = TDFRecord(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            provenance=TDFProvenance(generator="test"),
            payload={"key": "value"},
        )
        assert record.entity_ids == []

    def test_entity_ids_serialize_deserialize(self):
        record = TDFRecord(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            provenance=TDFProvenance(generator="test"),
            payload={"key": "value"},
            entity_ids=["figure-abc-123", "figure-def-456"],
        )
        assert record.entity_ids == ["figure-abc-123", "figure-def-456"]
        # Round-trip via dict
        data = record.model_dump()
        restored = TDFRecord(**data)
        assert restored.entity_ids == ["figure-abc-123", "figure-def-456"]

    def test_backward_compat_no_entity_ids(self):
        """Records without entity_ids field still parse (backward compat)."""
        data = {
            "id": "old-record",
            "source": "flash",
            "timestamp": "2024-03-15T14:00:00+00:00",
            "provenance": {"generator": "test"},
            "payload": {"key": "value"},
        }
        record = TDFRecord(**data)
        assert record.entity_ids == []

    def test_entity_ids_do_not_affect_hash(self):
        common = dict(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            provenance=TDFProvenance(generator="test"),
            payload={"same": "data"},
        )
        r1 = TDFRecord(entity_ids=[], **common)
        r2 = TDFRecord(entity_ids=["figure-abc-123", "figure-def-456"], **common)
        assert r1.tdf_hash == r2.tdf_hash

    def test_grounding_provenance_fields_default(self):
        prov = TDFProvenance(generator="test")
        assert prov.grounding_model is None
        assert prov.grounding_status is None
        assert prov.grounded_at is None

    def test_grounding_provenance_fields_do_not_affect_hash(self):
        common = dict(
            id="test-id",
            source="flash",
            timestamp=_sample_timestamp(),
            payload={"same": "data"},
        )
        r1 = TDFRecord(provenance=TDFProvenance(generator="test"), **common)
        r2 = TDFRecord(
            provenance=TDFProvenance(
                generator="test",
                grounding_model="perplexity/sonar",
                grounding_status="grounded",
                grounded_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc),
            ),
            **common,
        )
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
            "latitude": 51.9975,
            "longitude": -0.7413,
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
            "query",
            "slug",
            "year",
            "month",
            "day",
            "season",
            "time_of_day",
            "era",
            "location",
            "latitude",
            "longitude",
            "scene_data",
            "character_data",
            "dialog",
            "grounding_data",
            "moment_data",
            "metadata",
            "entity_ids",
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


class TestFromProteus:
    def test_basic_transform(self):
        resolution = {
            "market_id": 42,
            "resolved_at": "2026-03-04T18:30:00+00:00",
            "actor_handle": "elonmusk",
            "actual_text": "Starship flight 2 is GO for March.",
            "predicted_text": "Starship flight 2 confirmed for March.",
            "levenshtein_distance": 12,
            "winning_submission_id": "sub-001",
            "submission_count": 5,
            "total_pool": "0.05",
            "tx_hash": "0xabc123",
            "block_number": 12345678,
            "gas_used": 9000000,
        }
        record = from_proteus(resolution)
        assert record.id == "proteus-market-42"
        assert record.source == "proteus"
        assert record.provenance.generator == "proteus-markets"
        assert record.provenance.run_id == "42"
        assert record.payload["actor_handle"] == "elonmusk"
        assert record.payload["actual_text"] == "Starship flight 2 is GO for March."
        assert (
            record.payload["predicted_text"] == "Starship flight 2 confirmed for March."
        )
        assert record.payload["levenshtein_distance"] == 12
        assert record.payload["tx_hash"] == "0xabc123"
        assert record.payload["block_number"] == 12345678
        assert record.payload["gas_used"] == 9000000
        assert record.payload["submission_count"] == 5
        assert record.payload["total_pool"] == "0.05"
        assert record.payload["winning_submission_id"] == "sub-001"
        # Internal keys excluded from payload
        assert "market_id" not in record.payload
        assert "resolved_at" not in record.payload

    def test_missing_optional_fields_default_to_none(self):
        resolution = {
            "market_id": 7,
            "resolved_at": "2026-03-04T18:30:00+00:00",
        }
        record = from_proteus(resolution)
        assert record.id == "proteus-market-7"
        assert record.payload["actor_handle"] is None
        assert record.payload["actual_text"] is None
        assert record.payload["levenshtein_distance"] is None

    def test_timestamp_fallback(self):
        resolution = {"market_id": 1}
        record = from_proteus(resolution)
        assert record.timestamp is not None
        assert record.id == "proteus-market-1"


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

    def test_round_trip_with_model_provenance(self):
        records = [
            TDFRecord(
                id="record-prov",
                source="clockchain",
                timestamp=_sample_timestamp(),
                provenance=TDFProvenance(
                    generator="timepoint-clockchain",
                    text_model="deepseek-r1",
                    image_model="nvidia/flux-dev",
                    model_provider="openrouter",
                    model_permissiveness="permissive",
                    schema_version="0.2",
                    generation_id="gen-abc-123",
                ),
                payload={"title": "Test"},
            )
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            tmp_path = f.name

        try:
            write_tdf_jsonl(records, tmp_path)
            loaded = read_tdf_jsonl(tmp_path)
            assert len(loaded) == 1
            rec = loaded[0]
            assert rec.provenance.text_model == "deepseek-r1"
            assert rec.provenance.image_model == "nvidia/flux-dev"
            assert rec.provenance.model_provider == "openrouter"
            assert rec.provenance.model_permissiveness == "permissive"
            assert rec.provenance.schema_version == "0.2"
            assert rec.provenance.generation_id == "gen-abc-123"
        finally:
            os.unlink(tmp_path)


class TestGroundingProvenanceRoundTrip:
    def test_round_trip_with_grounding_provenance(self):
        records = [
            TDFRecord(
                id="record-grounding",
                source="flash",
                timestamp=_sample_timestamp(),
                provenance=TDFProvenance(
                    generator="timepoint-flash",
                    grounding_model="perplexity/sonar",
                    grounding_status="grounded",
                    grounded_at=datetime(2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc),
                ),
                payload={"title": "Grounded Test"},
            )
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            tmp_path = f.name

        try:
            write_tdf_jsonl(records, tmp_path)
            loaded = read_tdf_jsonl(tmp_path)
            assert len(loaded) == 1
            rec = loaded[0]
            assert rec.provenance.grounding_model == "perplexity/sonar"
            assert rec.provenance.grounding_status == "grounded"
            assert rec.provenance.grounded_at == datetime(
                2026, 3, 30, 12, 0, 0, tzinfo=timezone.utc
            )
        finally:
            os.unlink(tmp_path)


class TestFromClockchainV02:
    def test_v02_node_promotes_provenance_fields(self):
        node = {
            "path": "/2025/june/01/1200/us/test",
            "id": "cc-v02-uuid",
            "created_at": "2025-06-01T12:00:00+00:00",
            "flash_timepoint_id": "flash-uuid",
            "confidence": 0.9,
            "text_model": "deepseek-r1",
            "image_model": "nvidia/flux-dev",
            "model_provider": "openrouter",
            "model_permissiveness": "permissive",
            "schema_version": "0.2",
            "generation_id": "gen-001",
            "graph_state_hash": "abc123hash",
            "title": "V02 Event",
            "body": "Content here",
        }
        record = from_clockchain(node)
        assert record.provenance.text_model == "deepseek-r1"
        assert record.provenance.image_model == "nvidia/flux-dev"
        assert record.provenance.model_provider == "openrouter"
        assert record.provenance.model_permissiveness == "permissive"
        assert record.provenance.schema_version == "0.2"
        assert record.provenance.generation_id == "gen-001"
        # These should NOT be in payload
        assert "text_model" not in record.payload
        assert "image_model" not in record.payload
        assert "model_provider" not in record.payload
        assert "schema_version" not in record.payload
        assert "generation_id" not in record.payload
        assert "graph_state_hash" not in record.payload
        # Content stays in payload
        assert record.payload["title"] == "V02 Event"
        assert record.payload["body"] == "Content here"


class TestFromClockchainGrounding:
    def test_grounding_fields_carried_through(self):
        node = {
            "path": "/2026/march/30/1200/us/grounded-event",
            "id": "cc-grounded-uuid",
            "created_at": "2026-03-30T12:00:00+00:00",
            "grounding_model": "perplexity/sonar",
            "grounding_status": "grounded",
            "grounded_at": "2026-03-30T11:00:00+00:00",
            "title": "Grounded Event",
            "body": "Content",
        }
        record = from_clockchain(node)
        assert record.provenance.grounding_model == "perplexity/sonar"
        assert record.provenance.grounding_status == "grounded"
        assert record.provenance.grounded_at == datetime(2026, 3, 30, 11, 0, 0, tzinfo=timezone.utc)
        # Grounding fields should NOT be in payload
        assert "grounding_model" not in record.payload
        assert "grounding_status" not in record.payload
        assert "grounded_at" not in record.payload


class TestFromFlashGrounding:
    def test_grounding_fields_carried_through(self):
        timepoint = {
            "id": "flash-grounded-001",
            "created_at": "2026-03-30T12:00:00+00:00",
            "grounding_model": "perplexity/sonar",
            "grounding_status": "grounded",
            "grounded_at": "2026-03-30T11:00:00+00:00",
        }
        record = from_flash(timepoint)
        assert record.provenance.grounding_model == "perplexity/sonar"
        assert record.provenance.grounding_status == "grounded"
        assert record.provenance.grounded_at == datetime(2026, 3, 30, 11, 0, 0, tzinfo=timezone.utc)


class TestFromFlashModelProvenance:
    def test_model_fields_mapped(self):
        timepoint = {
            "id": "flash-model-001",
            "created_at": "2025-06-01T12:00:00+00:00",
            "text_model_used": "deepseek-r1",
            "image_model_used": "nvidia/flux-dev",
            "model_provider": "openrouter",
            "generation_id": "gen-flash-001",
        }
        record = from_flash(timepoint)
        assert record.provenance.text_model == "deepseek-r1"
        assert record.provenance.image_model == "nvidia/flux-dev"
        assert record.provenance.model_provider == "openrouter"
        assert record.provenance.model_permissiveness == "permissive"
        assert record.provenance.generation_id == "gen-flash-001"


class TestInferModelPermissiveness:
    def test_permissive_models(self):
        assert infer_model_permissiveness("deepseek-r1") == "permissive"
        assert infer_model_permissiveness("qwen-2.5") == "permissive"
        assert infer_model_permissiveness("meta-llama/llama-3") == "permissive"
        assert (
            infer_model_permissiveness("stabilityai/stable-diffusion-xl")
            == "permissive"
        )

    def test_restricted_models(self):
        assert infer_model_permissiveness("gemini-2.5-flash") == "restricted"
        assert infer_model_permissiveness("claude-3-opus") == "restricted"
        assert infer_model_permissiveness("gpt-4") == "restricted"

    def test_unknown_model(self):
        assert infer_model_permissiveness("some-custom-model") == "unknown"


class TestSchemaVersions:
    def test_has_expected_versions(self):
        assert "0.1" in SCHEMA_VERSIONS
        assert "0.2" in SCHEMA_VERSIONS
