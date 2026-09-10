"""Bulk Data $export support.

Modeled on HL7's Bulk Data Access IG (http://hl7.org/fhir/uv/bulkdata) async
kick-off/poll/download pattern: a client kicks off an export and gets a
polling URL back immediately (202), polls it until the job is done (200
with a manifest), then downloads NDJSON files named in the manifest. The IG
itself is published for FHIR R4 (see fhir/validation.py's module docstring
for the same R4-vs-R5 situation with US Core/IPS) — what's implemented here
is the *operation pattern*, serving R5 resources as NDJSON, not a claim of
IG conformance.

**Boundary, stated plainly:** jobs run synchronously at kick-off time and
are held in this process's memory (not Postgres, not any durable queue).
That means: results don't survive a restart, aren't shared across multiple
API instances, and this isn't suitable for datasets large enough to need a
real background worker. It's honest for a reference implementation's data
volumes and wrong for a production Bulk Data deployment — see
docs/ROADMAP.md.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class ExportOutput:
    resource_type: str
    count: int
    ndjson: str


@dataclass
class ExportJob:
    job_id: str
    status: str  # "completed" | "error" (jobs are always synchronous — see module docstring)
    transaction_time: str
    request_url: str
    outputs: list[ExportOutput] = field(default_factory=list)
    error: str | None = None
    created_at: float = field(default_factory=time.monotonic)

    def to_manifest(self, files_base_url: str) -> dict[str, Any]:
        return {
            "transactionTime": self.transaction_time,
            "request": self.request_url,
            "requiresAccessToken": True,
            "output": [
                {
                    "type": output.resource_type,
                    "url": f"{files_base_url}/{self.job_id}/{output.resource_type}.ndjson",
                    "count": output.count,
                }
                for output in self.outputs
            ],
            "error": [{"type": "OperationOutcome", "url": self.error}] if self.error else [],
        }


class ExportJobRegistry:
    """Thread-safe, in-memory job store. See module docstring for the
    single-process, non-durable boundary this implies."""

    def __init__(self) -> None:
        self._jobs: dict[str, ExportJob] = {}
        self._lock = threading.Lock()

    def create(
        self, *, request_url: str, outputs: list[ExportOutput], error: str | None = None
    ) -> ExportJob:
        job = ExportJob(
            job_id=str(uuid4()),
            status="error" if error else "completed",
            transaction_time=datetime.now(timezone.utc).isoformat(),
            request_url=request_url,
            outputs=outputs,
            error=error,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> ExportJob | None:
        with self._lock:
            return self._jobs.get(job_id)

    def delete(self, job_id: str) -> bool:
        with self._lock:
            return self._jobs.pop(job_id, None) is not None

    def evict_stale(self, older_than_seconds: float = 3600.0) -> int:
        now = time.monotonic()
        with self._lock:
            stale = [
                job_id
                for job_id, job in self._jobs.items()
                if now - job.created_at > older_than_seconds
            ]
            for job_id in stale:
                del self._jobs[job_id]
            return len(stale)


def resources_to_ndjson(resources: list[dict[str, Any]]) -> str:
    return "\n".join(json.dumps(resource, separators=(",", ":")) for resource in resources)
