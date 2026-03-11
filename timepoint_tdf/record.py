from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Literal
import hashlib
import json


class TDFProvenance(BaseModel):
    generator: str  # e.g. "timepoint-flash", "timepoint-clockchain"
    run_id: Optional[str] = None
    confidence: Optional[float] = None
    flash_id: Optional[str] = None  # Flash UUID when available (secondary reference)
    text_model: Optional[str] = None  # Model ID that generated text content
    image_model: Optional[str] = None  # Model ID that generated image content
    model_provider: Optional[str] = None  # Routing provider (google, openrouter, etc.)
    model_permissiveness: Optional[str] = None  # permissive, restricted, unknown
    schema_version: Optional[str] = "0.1"  # Clockchain schema version
    generation_id: Optional[str] = None  # Unique ID for the generation run


class TDFRecord(BaseModel):
    id: str  # Clockchain canonical URL when available, Flash UUID otherwise
    version: str = "1.0.0"
    source: Literal["clockchain", "flash", "pro", "proteus", "snag-bench"]
    timestamp: datetime
    provenance: TDFProvenance
    payload: dict
    tdf_hash: str = ""

    def model_post_init(self, __context):
        if not self.tdf_hash:
            self.tdf_hash = self.compute_hash()

    def compute_hash(self) -> str:
        """Hash payload only — provenance is metadata about the record, not content."""
        canonical = json.dumps(self.payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()
