"""Auto-pagination iterator for the AumOS Python SDK.

Allows iterating over all items in a paginated collection without
manually tracking page tokens:

    async for agent in client.agents.list_all():
        process(agent)

Memory usage is O(page_size), never O(total_items).
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Coroutine
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class AsyncPageIterator(Generic[T]):
    """Async iterator that automatically fetches subsequent pages.

    Args:
        first_page: The initial page response containing items and next_page_token.
        fetch_next: Async callable that accepts a page_token and returns the next page.

    Example:
        async for agent in AsyncPageIterator(first_page, client._fetch_agents_page):
            process(agent)
    """

    def __init__(
        self,
        first_page: Any,
        fetch_next: Callable[[str], Coroutine[Any, Any, Any]],
    ) -> None:
        self._current_page = first_page
        self._fetch_next = fetch_next
        self._index: int = 0

    def __aiter__(self) -> "AsyncPageIterator[T]":
        return self

    async def __anext__(self) -> T:
        """Return the next item, fetching the next page when the current one is exhausted."""
        items = self._current_page.items
        if self._index < len(items):
            item = items[self._index]
            self._index += 1
            return item  # type: ignore[return-value]

        next_token: str | None = getattr(self._current_page, "next_page_token", None)
        if not next_token:
            raise StopAsyncIteration

        self._current_page = await self._fetch_next(next_token)
        self._index = 0
        return await self.__anext__()


async def collect_all_pages(iterator: AsyncPageIterator[T]) -> list[T]:
    """Eagerly collect all items from a page iterator into a list.

    Warning: This buffers all results in memory. Prefer streaming with
    async for unless you need a complete list.

    Args:
        iterator: An AsyncPageIterator instance to drain.

    Returns:
        All items across all pages as a single list.
    """
    return [item async for item in iterator]
