import asyncio

from app.chat.manager import ConnectionManager


class FakeSocket:
    """Stands in for a real WebSocket. It only needs send_text,
    because that's the only thing broadcast_text calls."""

    def __init__(self, broken: bool = False):
        self.broken = broken
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        if self.broken:
            raise RuntimeError("connection is gone")
        self.sent.append(text)


def test_broadcast_skips_broken_connection():
    m = ConnectionManager()
    good, bad = FakeSocket(), FakeSocket(broken=True)
    m.connections.update({good, bad})

    # broadcast_text is async, so run it in a fresh event loop.
    asyncio.run(m.broadcast_text("hi"))

    assert good.sent == ["hi"]          # the healthy client still got it
    assert bad not in m.connections     # the dead one was dropped
