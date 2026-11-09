from collections import deque

from fastapi import WebSocket
from pydantic import BaseModel

from app.chat.schemas import ChatOut, UserLeftOut
from app.config import settings


class ConnectionManager:
    """Knows about every open connection, who has joined, and recent chat.

    The endpoint in chat.py handles ONE connection. The manager is the one
    place that knows about ALL of them. That's why it's a separate file.
    """

    def __init__(self, history_size: int) -> None:
        # Level 4: a dict instead of a set.
        #   key   = the connection
        #   value = the name it joined with, or None if it hasn't joined yet
        # Connected but not joined = not "in the room": no broadcasts, not counted online.
        self.connections: dict[WebSocket, str | None] = {}

        # Level 5: the last N chat messages, for catching up newcomers.
        # deque(maxlen=N) drops the OLDEST item by itself when a new one
        # is added to a full deque. No manual trimming needed.
        self.history: deque[ChatOut] = deque(maxlen=history_size)

    # ---------- connections and names ----------

    async def connect(self, websocket: WebSocket) -> None:
        """Finish the handshake, then start tracking this connection (not joined yet)."""
        await websocket.accept()
        self.connections[websocket] = None

    def set_name(self, websocket: WebSocket, name: str) -> None:
        """Mark this connection as joined under a name."""
        self.connections[websocket] = name

    def name_of(self, websocket: WebSocket) -> str | None:
        """The name this connection joined with, or None if it hasn't joined."""
        return self.connections.get(websocket)

    def disconnect(self, websocket: WebSocket) -> str | None:
        """Stop tracking a connection and return its name (None if it never joined,
        or was already removed). pop(..., None) makes calling this twice safe."""
        return self.connections.pop(websocket, None)

    def online_count(self) -> int:
        """How many connections have joined. Not-joined connections don't count."""
        return sum(1 for name in self.connections.values() if name is not None)

    # ---------- history ----------

    def remember(self, message: ChatOut) -> None:
        self.history.append(message)

    def recent(self) -> list[ChatOut]:
        """Oldest first, newest last: the order a chat window shows them."""
        return list(self.history)

    # ---------- sending ----------

    async def send(self, websocket: WebSocket, message: BaseModel) -> None:
        """Send one protocol message to ONE connection (for example welcome, pong or error)."""
        await websocket.send_text(message.model_dump_json())

    async def broadcast(self, message: BaseModel, exclude: WebSocket | None = None) -> None:
        """Send one protocol message to every JOINED connection, except `exclude`.

        If a send fails, that client is gone (closed tab, lost Wi-Fi): drop it,
        carry on with the others, then tell everyone it left.
        """
        # Turn the model into JSON once, not once per connection.
        text = message.model_dump_json()
        dropped: list[str] = []

        # Loop over a COPY. disconnect() changes self.connections, and
        # changing a dict while looping over it raises
        # "RuntimeError: dictionary changed size during iteration".
        for websocket, name in list(self.connections.items()):
            if name is None or websocket is exclude:
                continue
            try:
                await websocket.send_text(text)
            except Exception:
                # One dead client must not stop everyone else from getting the message.
                self.disconnect(websocket)
                dropped.append(name)

        # The subtle part: the dead client's own endpoint will notice later and
        # call disconnect() too, but by then it's already gone from the dict, so
        # disconnect() returns None and the endpoint announces nothing. So the
        # announcement has to happen here, or the user would vanish silently.
        for name in dropped:
            await self.broadcast(UserLeftOut(name=name, online=self.online_count()))


# One shared instance for the whole app. Every connection's endpoint uses
# this same object, so they all see the same connections and history.
manager = ConnectionManager(history_size=settings.history_size)
