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
        canonical = json.dumps(self.payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()
