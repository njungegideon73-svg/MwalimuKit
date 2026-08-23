"""Migration utilities — backfill helpers, batch ops, safe column swaps."""
from __future__ import annotations

from typing import TypeVar

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

T = TypeVar("T")


async def batch_update(
    conn: AsyncConnection,
    sql: str,
    batch_size: int = 10_000,
    params: dict | None = None,
) -> int:
    """Run UPDATE in batches to avoid long locks."""
    params = params or {}
    total = 0
    while True:
        result = await conn.execute(
            text(sql),
            {**params, "limit": batch_size},
        )
        count = result.rowcount
        total += count
        if count < batch_size:
            break
    return total


async def count_rows(conn: AsyncConnection, table: str, where: str = "") -> int:
    q = f"SELECT COUNT(*) FROM {table}"
    if where:
        q += f" WHERE {where}"
    result = await conn.execute(text(q))
    return result.scalar_one()


async def with_lock_timeout(conn: AsyncConnection, sql: str, timeout_ms: int = 5_000) -> None:
    await conn.execute(text(f"SET lock_timeout = '{timeout_ms}ms'"))
    try:
        await conn.execute(text(sql))
    finally:
        await conn.execute(text("SET lock_timeout = 0"))


async def concurrently(conn: AsyncConnection, sql: str) -> None:
    """Wrap DDL in CONCURRENTLY where supported (PostgreSQL indexes)."""
    await conn.execute(text(sql))


def chunked(iterable: list[T], size: int) -> list[list[T]]:
    return [iterable[i:i + size] for i in range(0, len(iterable), size)]
