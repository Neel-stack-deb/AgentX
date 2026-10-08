from abc import ABC, abstractmethod
import hashlib
import math
import re


class EmbeddingProvider(ABC):
    """Maps text to a dense vector. No memory or orchestration logic."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        pass

    @abstractmethod
    def embed(self, text: str) -> list[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        pass


class HashEmbeddingProvider(EmbeddingProvider):
    """
    Deterministic bag-of-words-style embeddings for development and tests.

    Similar texts overlap on tokens and yield higher cosine similarity.
    Replace with an HTTP/API-backed provider in production without changing MemoryManager.
    """

    def __init__(self, dimensions: int = 64) -> None:
        if dimensions < 8:
            raise ValueError("dimensions must be at least 8")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        return self._embed_one(text)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        if not tokens:
            return vector

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            vector[index] += 1.0

        return _l2_normalize(vector)


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]
