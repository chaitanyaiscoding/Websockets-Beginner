import asyncio
import json

from app.chat.manager import ConnectionManager
from app.chat.schemas import PongOut


class FakeSocket:
    """Stands in for a real WebSocket. It only needs send_text,
    because that's the only thing broadcast calls."""

    def __init__(self, broken: bool = False):
        self.broken = broken
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        if self.broken:
            raise RuntimeError("connection is gone")
        self.sent.append(text)


def test_broadcast_skips_broken_connection_and_announces_it():
    m = ConnectionManager(history_size=5)
    good, bad = FakeSocket(), FakeSocket(broken=True)
    # Both have joined: the value is their name.
    m.connections.update({good: "Good", bad: "Bad"})

    # broadcast is async, so run it in a fresh event loop.
    asyncio.run(m.broadcast(PongOut()))

    assert bad not in m.connections  # the dead one was dropped
    # The healthy client got the message, AND was told the dead one left.
    # Without this, "Bad" would vanish silently and the online count would be wrong.
    assert [json.loads(t) for t in good.sent] == [
        {"type": "pong"},
        {"type": "user_left", "name": "Bad", "online": 1},
    ]


def test_broadcast_can_skip_one_connection():
    m = ConnectionManager(history_size=5)
    a, b = FakeSocket(), FakeSocket()
    m.connections.update({a: "A", b: "B"})

    asyncio.run(m.broadcast(PongOut(), exclude=a))

    assert a.sent == []
    assert b.sent == ['{"type":"pong"}']
