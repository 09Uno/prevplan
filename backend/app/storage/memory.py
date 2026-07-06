from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

from app.domain.schemas import ComparisonResult
from app.planning.schemas import PlanningCase


class InMemoryCaseRepository:
    def __init__(self) -> None:
        self._items: dict[str, ComparisonResult] = {}

    def add(self, comparison: ComparisonResult) -> ComparisonResult:
        self._items[comparison.id] = comparison
        return comparison

    def list(self) -> list[ComparisonResult]:
        return sorted(self._items.values(), key=lambda item: item.created_at, reverse=True)

    def get(self, case_id: str) -> ComparisonResult | None:
        return self._items.get(case_id)


repository = InMemoryCaseRepository()


class InMemoryPlanningRepository:
    def __init__(self) -> None:
        self._items: dict[str, PlanningCase] = {}

    def add(self, planning_case: PlanningCase) -> PlanningCase:
        self._items[planning_case.id] = planning_case
        return planning_case

    def list(self) -> list[PlanningCase]:
        return sorted(self._items.values(), key=lambda item: item.created_at, reverse=True)

    def get(self, case_id: str) -> PlanningCase | None:
        return self._items.get(case_id)


class PostgresJsonRepository:
    def __init__(self, database_url: str, table_name: str, model: type[ComparisonResult] | type[PlanningCase]) -> None:
        self.database_url = database_url
        self.table_name = table_name
        self.model = model
        self._ensure_table()

    def add(self, item: ComparisonResult | PlanningCase) -> ComparisonResult | PlanningCase:
        from psycopg import connect
        from psycopg.types.json import Jsonb

        payload = item.model_dump(mode="json")
        created_at = parse_created_at(payload.get("created_at"))
        with connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    insert into {self.table_name} (id, created_at, payload)
                    values (%s, %s, %s)
                    on conflict (id) do update
                    set created_at = excluded.created_at,
                        payload = excluded.payload
                    """,
                    (item.id, created_at, Jsonb(payload)),
                )
        return item

    def list(self) -> list[ComparisonResult] | list[PlanningCase]:
        from psycopg import connect

        with connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"select payload from {self.table_name} order by created_at desc limit 200"
                )
                return [self.model.model_validate(row[0]) for row in cursor.fetchall()]

    def get(self, case_id: str) -> ComparisonResult | PlanningCase | None:
        from psycopg import connect

        with connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f"select payload from {self.table_name} where id = %s", (case_id,))
                row = cursor.fetchone()
                if not row:
                    return None
                return self.model.model_validate(row[0])

    def _ensure_table(self) -> None:
        from psycopg import connect

        with connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    create table if not exists {self.table_name} (
                        id text primary key,
                        created_at timestamptz not null,
                        payload jsonb not null
                    )
                    """
                )
                cursor.execute(
                    f"""
                    create index if not exists {self.table_name}_created_at_idx
                    on {self.table_name} (created_at desc)
                    """
                )


def parse_created_at(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return datetime.now(UTC)


def build_repository(table_name: str, model: type[ComparisonResult] | type[PlanningCase]):
    database_url = os.getenv("DATABASE_URL", "").strip()
    if database_url:
        return PostgresJsonRepository(database_url, table_name, model)
    if model is ComparisonResult:
        return InMemoryCaseRepository()
    return InMemoryPlanningRepository()


repository = build_repository("comparison_cases", ComparisonResult)
planning_repository = build_repository("planning_cases", PlanningCase)
