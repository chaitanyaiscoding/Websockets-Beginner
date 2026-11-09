from fastapi import WebSocket


class ConnectionManager:
    """Knows about every open connection, and sends messages to all of them.

    The endpoint in chat.py handles ONE connection. The manager is the one
    place that knows about ALL of them. That's why it's a separate file.
    """

    def __init__(self) -> None:
        # A set: each connection appears once, and removing is fast.
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Finish the handshake, then start tracking this connection."""
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Stop tracking a connection. discard (not remove) means calling
        this twice for the same socket is safe, with no KeyError."""
        self.connections.discard(websocket)

    async def broadcast_text(self, text: str) -> None:
        """Send text to every connection. If one send fails, drop that
        connection and carry on with the others."""
        # Loop over a COPY. disconnect() changes self.connections, and
        # changing a set while looping over it raises
        # "RuntimeError: Set changed size during iteration".
        for websocket in list(self.connections):
            try:
                await websocket.send_text(text)
            except Exception:
                # The client vanished (closed tab, lost Wi-Fi) before we noticed.
                # One dead client must not stop everyone else from getting the message.
                self.disconnect(websocket)


# One shared instance for the whole app. Every connection's endpoint uses
# this same object, so they all see the same set of connections.
manager = ConnectionManager()
