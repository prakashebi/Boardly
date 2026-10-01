from dataclasses import dataclass


@dataclass
class SearchResult:
    entity_id: str
    entity_type: str
    title: str
    description: str | None
    score: float


class SearchService:
    def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchResult]:
        raise NotImplementedError

    def index_entity(
        self,
        entity_id: str,
        entity_type: str,
        title: str,
        description: str | None,
        metadata: dict | None = None,
    ) -> None:
        raise NotImplementedError

    def update_entity(
        self,
        entity_id: str,
        title: str,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        raise NotImplementedError

    def delete_entity(self, entity_id: str) -> None:
        raise NotImplementedError
