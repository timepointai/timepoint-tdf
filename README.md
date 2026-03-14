# timepoint-tdf

**Timepoint Data Format** — a canonical envelope for temporal causal data across the Timepoint suite.

Every service in Timepoint (Flash, Pro, Clockchain, SNAG-Bench, Proteus) produces structurally different data — historical scenes, causal simulations, graph nodes, quality scores, predictions. TDF normalizes all of them into a single content-addressed record type so downstream consumers can ingest any record without knowing which service produced it.

**Design principle:** uniform envelope, varying payload. The six envelope fields (`id`, `source`, `timestamp`, `provenance`, `payload`, `tdf_hash`) are fixed across all sources. The `payload` dict schema varies by source. The `tdf_hash` (SHA-256 of the canonicalized payload) gives you content-addressable deduplication when the same event flows through multiple services.

```mermaid
flowchart LR
    Flash --> TDF(["TDF Record"])
    Pro --> TDF
    CC[Clockchain] --> TDF
    TDF --> SB[SNAG-Bench]
    TDF --> Proteus
    TDF --> CC
```

## Record Model

Every `TDFRecord` shares this envelope:

| Field | Type | Description |
|-------|------|-------------|
| `id` | str | Clockchain canonical URL or Flash/Pro UUID |
| `source` | Literal | `clockchain`, `flash`, `pro`, `proteus`, `snag-bench` |
| `timestamp` | datetime | When the record was created |
| `provenance` | TDFProvenance | Lineage: generator, run_id, confidence, flash_id |
| `payload` | dict | **Source-specific content** (see payload schemas below) |
| `tdf_hash` | str | SHA-256 of canonicalized payload (content-addressed) |

`TDFProvenance` tracks cross-service lineage — `flash_id` preserves the originating Flash UUID even when the canonical `id` is a Clockchain URL, so you can always trace a record back to its source rendering.

## Payload Schemas by Source

The payload is where data diverges. Each transform projects source-specific fields into the payload:

**Flash** — full spatio-temporal-narrative content of a rendered historical moment (16 fields):

`query`, `slug`, `year`, `month`, `day`, `season`, `time_of_day`, `era`, `location`, `scene_data`, `character_data`, `dialog`, `grounding_data`, `moment_data`, `metadata`

**Pro** — causal simulation output (4 fields):

`entities`, `dialogs`, `causal_edges`, `metadata`

**Clockchain** — graph node pass-through (all node fields minus internal keys like `path`, `created_at`, `confidence`; confidence is promoted into `provenance`)

## Example Record

A Flash scene rendered as TDF:

```json
{
  "id": "a1b2c3d4-...",
  "version": "1.0.0",
  "source": "flash",
  "timestamp": "2026-03-01T12:00:00Z",
  "provenance": {
    "generator": "timepoint-flash",
    "run_id": null,
    "confidence": null,
    "flash_id": "a1b2c3d4-..."
  },
  "payload": {
    "query": "assassination of Archduke Franz Ferdinand",
    "slug": "franz-ferdinand-assassination",
    "year": 1914, "month": 6, "day": 28,
    "season": "summer",
    "time_of_day": "morning",
    "era": "early_20th_century",
    "location": "Sarajevo, Bosnia",
    "scene_data": { "..." : "..." },
    "character_data": { "..." : "..." },
    "dialog": [ "..." ],
    "grounding_data": { "..." : "..." },
    "moment_data": { "..." : "..." },
    "metadata": { "..." : "..." }
  },
  "tdf_hash": "e3b0c44298fc1c14..."
}
```

## Transforms

| Function | Input | Output |
|----------|-------|--------|
| `from_flash(timepoint)` | Flash scene dict | TDFRecord with 16-field payload |
| `from_pro(run_data)` | Pro run output dict | TDFRecord with causal graph payload |
| `from_clockchain(node)` | Clockchain node dict | TDFRecord with canonical URL as id, confidence in provenance |

## I/O

Records serialize to JSONL — one JSON object per line, streamable into any training pipeline:

```python
from timepoint_tdf import TDFRecord, from_flash, write_tdf_jsonl, read_tdf_jsonl

record = from_flash(timepoint_dict)
write_tdf_jsonl([record], "output.jsonl")
records = read_tdf_jsonl("output.jsonl")
```

## Install

```bash
pip install -e .
```

Requires Python 3.10+ and Pydantic 2.0+.

## Changelog

### v1.2.2 (2026-03-14)

- Add `nousresearch` to permissive model prefix allowlist (Hermes family)
- All NVIDIA Nemotron and NousResearch Hermes models now correctly classified as permissive

### v1.2.1 (2026-03-13)

- Add `stabilityai` to permissive model allowlist
- Security: remove private repo references from README

### v1.1.0 (2026-03-02)

- `from_flash()` now extracts all 16 fields from Flash timepoints
- Missing optional fields default to `None` instead of being omitted
- Branch protection enforced on `main` (1 approval required, no force pushes)

## Timepoint Suite

Open-source engines for temporal AI. Render the past. Simulate the future. Score the predictions. Accumulate the graph.

| Service | Type | Repo | Role |
|---------|------|------|------|
| **Flash** | Open Source | timepoint-flash | Reality Writer — renders grounded historical moments (Synthetic Time Travel) |
| **Pro** | Open Source | timepoint-pro | Rendering Engine — SNAG-powered simulation, TDF output, training data |
| **Clockchain** | Open Source | timepoint-clockchain | Temporal Causal Graph — Rendered Past + Rendered Future, growing 24/7 |
| **SNAG Bench** | Open Source | timepoint-snag-bench | Quality Certifier — measures Causal Resolution across renderings |
| **Proteus** | Open Source | proteus | Settlement Layer — prediction markets that validate Rendered Futures |
| **TDF** | **Open Source** | **timepoint-tdf** | **Data Format — JSON-LD interchange across all services** |

## License

Apache-2.0
