from abc import ABC, abstractmethod
from datetime import datetime, timezone

from Types.Memory import Memory, MemoryStatus


class MemoryStore(ABC):
    """Authoritative store for Memory records (metadata + content)."""

    @abstractmethod
    def save(self, memory: Memory) -> Memory:
        pass

    @abstractmethod
    def get(self, memory_id: str) -> Memory | None:
        pass

    @abstractmethod
    def update(self, memory: Memory) -> Memory:
        pass

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        pass

    @abstractmethod
    def list_active(self) -> list[Memory]:
        pass


class InMemoryMemoryStore(MemoryStore):
    def __init__(self) -> None:
        self._records: dict[str, Memory] = {}

    def save(self, memory: Memory) -> Memory:
        self._records[memory.memory_id] = memory
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self._records.get(memory_id)

    def update(self, memory: Memory) -> Memory:
        if memory.memory_id not in self._records:
            raise KeyError(f"memory not found: {memory.memory_id}")
        updated = memory.model_copy(
            update={"updated_at": datetime.now(timezone.utc)},
        )
        self._records[memory.memory_id] = updated
        return updated

    def delete(self, memory_id: str) -> bool:
        existing = self._records.get(memory_id)
        if existing is None:
            return False
        self._records[memory_id] = existing.model_copy(
            update={
                "status": MemoryStatus.DELETED,
                "updated_at": datetime.now(timezone.utc),
            },
        )
        return True

    def list_active(self) -> list[Memory]:
        return [
            memory
            for memory in self._records.values()
            if memory.status == MemoryStatus.ACTIVE
        ]
