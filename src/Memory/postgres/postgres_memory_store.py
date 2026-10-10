from Memory.memory_store import MemoryStore
from Memory.postgres.repository import PostgresMemoryRepository
from Types.Memory import Memory


class PostgresMemoryStore(MemoryStore):
    def __init__(self, repository: PostgresMemoryRepository) -> None:
        self._repository = repository

    def save(self, memory: Memory) -> Memory:
        return self._repository.save_memory(memory)

    def get(self, memory_id: str) -> Memory | None:
        return self._repository.get_memory(memory_id)

    def update(self, memory: Memory) -> Memory:
        return self._repository.update_memory(memory)

    def delete(self, memory_id: str) -> bool:
        return self._repository.delete_memory(memory_id)

    def list_active(self) -> list[Memory]:
        return self._repository.list_active_memories()
