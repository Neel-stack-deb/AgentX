import pytest

from Memory.embedding_provider import HashEmbeddingProvider
from Memory.embedding_validation import validate_embedding_vector
from Memory.exceptions import EmbeddingDimensionError


def test_rejects_wrong_embedding_dimension():
    with pytest.raises(EmbeddingDimensionError):
        validate_embedding_vector([0.1, 0.2], expected_dimension=32)


def test_accepts_matching_dimension():
    provider = HashEmbeddingProvider(dimensions=16)
    vector = provider.embed("hello")
    validate_embedding_vector(vector, expected_dimension=16)
