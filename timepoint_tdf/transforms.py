from datetime import datetime, timezone

from .record import TDFProvenance, TDFRecord

SCHEMA_VERSIONS = {
    "0.1": "Original 4 edge types, no model tracking",
    "0.2": "11 edge types, model provenance, graph state hash",
}

_PERMISSIVE_PREFIXES = (
    "deepseek",
    "qwen",
    "meta-llama",
    "mistralai",
    "nvidia",
    "stabilityai",
)
_RESTRICTED_PREFIXES = ("google", "gemini", "anthropic", "claude", "openai", "gpt")


def infer_model_permissiveness(model_id: str) -> str:
    """Infer license permissiveness from a model ID string."""
    lower = model_id.lower()
    for prefix in _PERMISSIVE_PREFIXES:
        if prefix in lower:
            return "permissive"
    for prefix in _RESTRICTED_PREFIXES:
        if prefix in lower:
            return "restricted"
    return "unknown"


def from_clockchain(node: dict) -> TDFRecord:
    """Transform a clockchain node dict to TDF."""
    record_id = node.get("path") or node["id"]
    internal_keys = {
        "path",
        "id",
        "created_at",
        "updated_at",
        "flash_timepoint_id",
        "confidence",
        "text_model",
        "image_model",
        "model_provider",
        "model_permissiveness",
        "schema_version",
        "generation_id",
        "graph_state_hash",
        "grounding_model",
        "grounding_status",
        "grounded_at",
    }
    payload = {k: v for k, v in node.items() if k not in internal_keys}

    timestamp = node["created_at"]
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    record = TDFRecord(
        id=record_id,
        source="clockchain",
        timestamp=timestamp,
        provenance=TDFProvenance(
            generator="timepoint-clockchain",
            flash_id=node.get("flash_timepoint_id"),
            confidence=node.get("confidence"),
            text_model=node.get("text_model"),
            image_model=node.get("image_model"),
            model_provider=node.get("model_provider"),
            model_permissiveness=node.get("model_permissiveness"),
            schema_version=node.get("schema_version", "0.1"),
            generation_id=node.get("generation_id"),
            grounding_model=node.get("grounding_model"),
            grounding_status=node.get("grounding_status"),
            grounded_at=node.get("grounded_at"),
        ),
        payload=payload,
    )
    entity_ids = payload.get("entity_ids", [])
    if entity_ids:
        record.entity_ids = entity_ids
    return record


_FLASH_PAYLOAD_KEYS = (
    "query",
    "slug",
    "year",
    "month",
    "day",
    "season",
    "time_of_day",
    "era",
    "location",
    "scene_data",
    "character_data",
    "dialog",
    "grounding_data",
    "moment_data",
    "metadata",
    "entity_ids",
)


def from_flash(timepoint: dict) -> TDFRecord:
    """Transform a Flash timepoint dict to TDF.

    Payload includes the full temporal-spatial-narrative content:
    query, slug, year, month, day, season, time_of_day, era, location,
    scene_data, character_data, dialog, grounding_data, moment_data, metadata.
    """
    timestamp = timepoint["created_at"]
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    payload = {k: timepoint.get(k) for k in _FLASH_PAYLOAD_KEYS}

    text_model = timepoint.get("text_model_used")
    image_model = timepoint.get("image_model_used")

    record = TDFRecord(
        id=timepoint["id"],
        source="flash",
        timestamp=timestamp,
        provenance=TDFProvenance(
            generator="timepoint-flash",
            flash_id=timepoint["id"],
            text_model=text_model,
            image_model=image_model,
            model_provider=timepoint.get("model_provider"),
            model_permissiveness=infer_model_permissiveness(text_model)
            if text_model
            else None,
            generation_id=timepoint.get("generation_id"),
            grounding_model=timepoint.get("grounding_model"),
            grounding_status=timepoint.get("grounding_status"),
            grounded_at=timepoint.get("grounded_at"),
        ),
        payload=payload,
    )
    entity_ids = payload.get("entity_ids", [])
    if entity_ids:
        record.entity_ids = entity_ids
    return record


def from_pro(run_data: dict) -> TDFRecord:
    """Transform a Pro run output dict to TDF."""
    timestamp = run_data.get("created_at", datetime.now(timezone.utc))
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    payload = {
        k: v
        for k, v in run_data.items()
        if k in ("entities", "dialogs", "causal_edges", "metadata")
    }

    return TDFRecord(
        id=run_data["run_id"],
        source="pro",
        timestamp=timestamp,
        provenance=TDFProvenance(
            generator="timepoint-pro",
            run_id=run_data["run_id"],
        ),
        payload=payload,
    )


_PROTEUS_PAYLOAD_KEYS = (
    "actor_handle",
    "actual_text",
    "predicted_text",
    "levenshtein_distance",
    "winning_submission_id",
    "submission_count",
    "total_pool",
    "tx_hash",
    "block_number",
    "gas_used",
)


def from_proteus(resolution: dict) -> TDFRecord:
    """Transform a Proteus market resolution dict to TDF.

    Payload includes market resolution data: actor_handle, actual_text,
    predicted_text, levenshtein_distance, winning_submission_id,
    submission_count, total_pool, tx_hash, block_number, gas_used.
    """
    timestamp = resolution.get("resolved_at", datetime.now(timezone.utc))
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    payload = {k: resolution.get(k) for k in _PROTEUS_PAYLOAD_KEYS}

    market_id = resolution.get("market_id")

    return TDFRecord(
        id=f"proteus-market-{market_id}",
        source="proteus",
        timestamp=timestamp,
        provenance=TDFProvenance(
            generator="proteus-markets",
            run_id=str(market_id),
        ),
        payload=payload,
    )
