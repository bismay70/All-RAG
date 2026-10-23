import time
from contextlib import contextmanager
from typing import Iterator

from app.schemas.common import TraceEvent


class LocalTrace:
    def __init__(self) -> None:
        self.events: list[TraceEvent] = []

    @contextmanager
    def node(self, name: str, message: str = "", **metadata: object) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
            self.add(name, "ok", message, metadata, (time.perf_counter() - start) * 1000)
        except Exception as exc:
            self.add(name, "error", str(exc), metadata, (time.perf_counter() - start) * 1000)
            raise

    def add(
        self,
        node: str,
        status: str = "ok",
        message: str = "",
        metadata: dict | None = None,
        elapsed_ms: float | None = None,
    ) -> None:
        self.events.append(
            TraceEvent(
                node=node,
                status=status,
                message=message,
                metadata=metadata or {},
                elapsed_ms=elapsed_ms,
            )
        )

