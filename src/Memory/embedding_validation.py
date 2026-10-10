from Memory.embedding_provider import EmbeddingProvider
from Memory.exceptions import EmbeddingDimensionError, EmbeddingModelMismatchError


def validate_embedding_vector(
    embedding: list[float],
    *,
    expected_dimension: int,
    expected_model: str | None = None,
    actual_model: str | None = None,
) -> None:
    if len(embedding) != expected_dimension:
        raise EmbeddingDimensionError(
            f"embedding length {len(embedding)} does not match expected dimension {expected_dimension}"
        )
    if expected_model is not None and actual_model is not None:
        if expected_model != actual_model:
            raise EmbeddingModelMismatchError(
                f"embedding model {actual_model!r} does not match expected {expected_model!r}"
            )


def validate_provider_embedding(
    provider: EmbeddingProvider,
    embedding: list[float],
) -> None:
    validate_embedding_vector(
        embedding,
        expected_dimension=provider.dimensions,
        expected_model=None,
        actual_model=provider.model_name,
    )
