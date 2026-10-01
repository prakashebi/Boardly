import logging

from .base import SearchResult, SearchService

logger = logging.getLogger(__name__)

INDEX_NAME = "orqestra_entities"

INDEX_MAPPING = {
    "mappings": {
        "properties": {
            "entity_id":   {"type": "keyword"},
            "entity_type": {"type": "keyword"},
            "title":       {"type": "text", "analyzer": "english"},
            "description": {"type": "text", "analyzer": "english"},
            "metadata":    {"type": "object", "enabled": False},
        }
    }
}


class OpenSearchService(SearchService):
    def __init__(self, host: str, port: int, user: str, password: str) -> None:
        from opensearchpy import OpenSearch

        self._client = OpenSearch(
            hosts=[{"host": host, "port": port}],
            http_auth=(user, password),
            use_ssl=True,
            verify_certs=False,
            ssl_show_warn=False,
        )
        self._ensure_index()

    def _ensure_index(self) -> None:
        if not self._client.indices.exists(index=INDEX_NAME):
            self._client.indices.create(index=INDEX_NAME, body=INDEX_MAPPING)
            logger.info("Created OpenSearch index '%s'", INDEX_NAME)

    def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchResult]:
        must: list[dict] = [
            {
                "multi_match": {
                    "query": query,
                    "fields": ["title^3", "description"],
                    "type": "best_fields",
                    "fuzziness": "AUTO",
                }
            }
        ]
        if entity_types:
            must.append({"terms": {"entity_type": entity_types}})

        body = {
            "query": {"bool": {"must": must}},
            "from": offset,
            "size": limit,
        }

        response = self._client.search(index=INDEX_NAME, body=body)
        hits = response["hits"]["hits"]
        return [
            SearchResult(
                entity_id=hit["_source"]["entity_id"],
                entity_type=hit["_source"]["entity_type"],
                title=hit["_source"]["title"],
                description=hit["_source"].get("description"),
                score=hit["_score"],
            )
            for hit in hits
        ]

    def index_entity(
        self,
        entity_id: str,
        entity_type: str,
        title: str,
        description: str | None,
        metadata: dict | None = None,
    ) -> None:
        self._client.index(
            index=INDEX_NAME,
            id=entity_id,
            body={
                "entity_id": entity_id,
                "entity_type": entity_type,
                "title": title,
                "description": description,
                "metadata": metadata or {},
            },
            refresh="wait_for",
        )

    def update_entity(
        self,
        entity_id: str,
        title: str,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        self._client.update(
            index=INDEX_NAME,
            id=entity_id,
            body={
                "doc": {
                    "title": title,
                    "description": description,
                    "metadata": metadata or {},
                }
            },
            refresh="wait_for",
        )

    def delete_entity(self, entity_id: str) -> None:
        self._client.delete(index=INDEX_NAME, id=entity_id, ignore=[404])
