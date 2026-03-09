from datetime import datetime, timezone

from .record import TDFProvenance, TDFRecord


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
    }
    payload = {k: v for k, v in node.items() if k not in internal_keys}

    timestamp = node["created_at"]
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    return TDFRecord(
        id=record_id,
        source="clockchain",
        timestamp=timestamp,
        provenance=TDFProvenance(
            generator="timepoint-clockchain",
            flash_id=node.get("flash_timepoint_id"),
            confidence=node.get("confidence"),
        ),
        payload=payload,
    )


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

    return TDFRecord(
        id=timepoint["id"],
        source="flash",
        timestamp=timestamp,
        provenance=TDFProvenance(
            generator="timepoint-flash",
            flash_id=timepoint["id"],
        ),
        payload=payload,
    )


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
