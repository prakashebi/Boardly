from django.conf import settings

from .base import SearchService


def get_search_service() -> SearchService:
    if settings.SEARCH_BACKEND == "opensearch":
        from .opensearch_service import OpenSearchService
        return OpenSearchService(
            host=settings.OPENSEARCH_HOST,
            port=settings.OPENSEARCH_PORT,
            user=settings.OPENSEARCH_USER,
            password=settings.OPENSEARCH_PASSWORD,
        )

    from .postgres import PostgresSearchService
    return PostgresSearchService()
