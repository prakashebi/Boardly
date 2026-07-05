from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.entity import Entity

from .base import SearchResult, SearchService


class PostgresSearchService(SearchService):
    """Full-text search backed by PostgreSQL tsvector — no extra infrastructure required."""

    def search(
        self,
        query: str,
        entity_types: list[str] | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[SearchResult]:
        # Build tsvector over title + description and rank by relevance
        tsvector = func.to_tsvector(
            "english",
            func.concat_ws(" ", func.coalesce(Entity.title, ""), func.coalesce(Entity.description, "")),
        )
        tsquery = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank(tsvector, tsquery)

        stmt = (
            select(Entity, rank.label("score"))
            .where(
                Entity.is_deleted.is_(False),
                tsvector.op("@@")(tsquery),
            )
            .order_by(rank.desc())
            .limit(limit)
            .offset(offset)
        )

        if entity_types:
            stmt = stmt.where(Entity.entity_type.in_(entity_types))

        with SessionLocal() as db:
            rows = db.execute(stmt).all()
        return [
            SearchResult(
                entity_id=str(row.Entity.id),
                entity_type=row.Entity.entity_type,
                title=row.Entity.title,
                description=row.Entity.description,
                score=float(row.score),
            )
            for row in rows
        ]

    # Postgres queries the live table directly — no separate index to maintain.
    def index_entity(self, entity_id, entity_type, title, description, metadata=None) -> None:
        pass

    def update_entity(self, entity_id, title, description=None, metadata=None) -> None:
        pass

    def delete_entity(self, entity_id: str) -> None:
        pass
