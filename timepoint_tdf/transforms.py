from datetime import datetime, timezone
from typing import Any

from .record import TDFProvenance, TDFRecord


def from_clockchain(node: dict) -> TDFRecord:
    """Transform a clockchain node dict to TDF."""
    record_id = node.get("path") or node["id"]
    internal_keys = {"path", "id", "created_at", "updated_at", "flash_timepoint_id", "confidence"}
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


def from_flash(timepoint: dict) -> TDFRecord:
    """Transform a Flash timepoint dict to TDF."""
    timestamp = timepoint["created_at"]
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp)

    payload = {
        k: v
        for k, v in timepoint.items()
        if k in ("scene_data", "character_data", "dialog", "metadata")
    }

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
