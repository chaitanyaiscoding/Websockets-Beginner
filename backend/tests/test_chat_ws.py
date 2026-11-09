from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_echo():
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello, WebSocket!")
        data = websocket.receive_text()
        assert data == "Message text was: Hello, WebSocket!"


def test_broadcast_reaches_every_client():
    # Two clients connected at the same time.
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_text("hi")
        # The sender is one of "everyone", so it gets its own message back too.
        assert a.receive_text() == "Message text was: hi"
        assert b.receive_text() == "Message text was: hi"
