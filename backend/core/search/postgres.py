from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.db.models import F, Value, CharField
from django.db.models.functions import Concat

from core.models import Entity
from .base import SearchResult, SearchService


class PostgresSearchService(SearchService):
    def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchResult]:
        search_vector = SearchVector("title", weight="A") + SearchVector("description", weight="B")
        search_query = SearchQuery(query, search_type="websearch")

        qs = Entity.objects.filter(
            is_deleted=False,
        ).annotate(
            search=search_vector,
            rank=SearchRank(search_vector, search_query),
        ).filter(
            search=search_query,
        ).order_by("-rank")

        if entity_types:
            qs = qs.filter(entity_type__in=entity_types)

        qs = qs[offset:offset+limit]

        return [
            SearchResult(
                entity_id=str(row.id),
                entity_type=row.entity_type,
                title=row.title,
                description=row.description,
                score=float(row.rank) if row.rank else 0.0,
            )
            for row in qs
        ]

    def index_entity(self, entity_id, entity_type, title, description, metadata=None) -> None:
        pass

    def update_entity(self, entity_id, title, description=None, metadata=None) -> None:
        pass

    def delete_entity(self, entity_id: str) -> None:
        pass
