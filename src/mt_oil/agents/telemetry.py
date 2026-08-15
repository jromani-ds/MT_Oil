"""Structured Cloud Logging telemetry for the wellfile agent."""

import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


def emit_agent_telemetry(
    api_number: str,
    gcs_uri: Optional[str],
    input_tokens: Optional[int],
    output_tokens: Optional[int],
    latency_ms: float,
    cache_hit: bool,
):
    logger.info(
        "wellfile_agent run complete",
        extra={
            "api_number": api_number,
            "gcs_uri": gcs_uri or "",
            "input_tokens": input_tokens or 0,
            "output_tokens": output_tokens or 0,
            "latency_ms": round(latency_ms, 1),
            "cache_hit": cache_hit,
        },
    )


class Timer:
    def __init__(self):
        self.start: float = 0.0

    def __enter__(self):
        self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        pass

    @property
    def elapsed_ms(self) -> float:
        return (time.monotonic() - self.start) * 1000
