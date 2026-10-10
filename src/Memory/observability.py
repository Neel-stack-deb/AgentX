import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field

from Memory.vector_store import VectorSearchStrategy

logger = logging.getLogger("agentx.memory")


@dataclass
class RetrievalObservation:
    backend: str
    search_strategy: VectorSearchStrategy | None = None
    top_k: int = 0
    result_count: int = 0
    filters_applied: dict[str, str | None] = field(default_factory=dict)
    latency_ms: float = 0.0
    error: str | None = None


@contextmanager
def observe_retrieval(backend: str, search_strategy: VectorSearchStrategy | None):
    start = time.perf_counter()
    observation = RetrievalObservation(backend=backend, search_strategy=search_strategy)
    try:
        yield observation
    except Exception as exc:
        observation.error = type(exc).__name__
        logger.warning(
            "memory retrieval failed backend=%s strategy=%s error=%s",
            backend,
            search_strategy,
            observation.error,
        )
        raise
    finally:
        observation.latency_ms = (time.perf_counter() - start) * 1000.0
        logger.info(
            "memory retrieval backend=%s strategy=%s top_k=%s results=%s latency_ms=%.2f filters=%s",
            observation.backend,
            observation.search_strategy,
            observation.top_k,
            observation.result_count,
            observation.latency_ms,
            observation.filters_applied,
        )
