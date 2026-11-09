import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.main import app

client = TestClient(app)

# Level 3: every message is JSON with a "type" field.
# The plain-text echo/broadcast tests from Levels 1–2 are replaced by these.


def test_chat_is_broadcast_as_json():
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        a.send_json({"type": "chat", "text": "hi"})
        a.receive_json()  # the sender gets its own copy too
        got = b.receive_json()
        assert got["type"] == "chat"
        assert got["text"] == "hi"
        assert "sent_at" in got  # the server adds the time, not the browser


def test_invalid_json_gets_error_and_connection_stays_open():
    with client.websocket_connect("/ws") as ws:
        ws.send_text("not json")
        assert ws.receive_json()["type"] == "error"
        # Still connected: a bad message must not kill the connection.
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}


def test_unknown_type_gets_error():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "dance"})
        assert ws.receive_json()["type"] == "error"


def test_too_long_text_gets_error():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat", "text": "x" * 1001})
        assert ws.receive_json()["type"] == "error"


def test_blank_chat_gets_error():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat", "text": "   "})
        assert ws.receive_json()["type"] == "error"


def test_unicode_text_round_trips():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat", "text": "నమస్తే 👋"})
        assert ws.receive_json()["text"] == "నమస్తే 👋"


def test_foreign_origin_is_refused():
    # A page on another website tries to connect: the server refuses
    # before accepting, so the connection never opens.
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/ws", headers={"origin": "http://evil.example"}):
            pass


def test_allowed_origin_connects():
    with client.websocket_connect("/ws", headers={"origin": "http://localhost:3000"}) as ws:
        ws.send_json({"type": "ping"})
        assert ws.receive_json() == {"type": "pong"}
