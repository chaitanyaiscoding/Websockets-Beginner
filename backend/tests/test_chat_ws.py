import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.config import settings
from app.main import app

client = TestClient(app)


def join(ws, name):
    """Send a join and return the reply (a welcome, or an error)."""
    ws.send_json({"type": "join", "name": name})
    return ws.receive_json()


# ---------- Level 3: JSON protocol and validation ----------


def test_chat_is_broadcast_as_json():
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as b:
        join(a, "Asha")
        join(b, "Ben")
        a.receive_json()  # user_joined Ben
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
        join(ws, "Asha")
        ws.send_json({"type": "chat", "text": "x" * 1001})
        assert ws.receive_json()["type"] == "error"


def test_blank_chat_gets_error():
    with client.websocket_connect("/ws") as ws:
        join(ws, "Asha")
        ws.send_json({"type": "chat", "text": "   "})
        assert ws.receive_json()["type"] == "error"


def test_unicode_text_round_trips():
    with client.websocket_connect("/ws") as ws:
        join(ws, "Asha")
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


# ---------- Level 4: join, leave, online count ----------


def test_join_gets_welcome_with_online_count():
    with client.websocket_connect("/ws") as a:
        assert join(a, "Asha") == {"type": "welcome", "history": [], "online": 1}


def test_others_hear_about_join_and_leave():
    with client.websocket_connect("/ws") as a:
        join(a, "Asha")
        with client.websocket_connect("/ws") as b:
            join(b, "Ben")
            assert a.receive_json() == {"type": "user_joined", "name": "Ben", "online": 2}
        # Leaving the inner "with" closed Ben's connection.
        assert a.receive_json() == {"type": "user_left", "name": "Ben", "online": 1}


def test_chat_before_join_gets_error():
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "chat", "text": "hi"})
        assert ws.receive_json() == {"type": "error", "message": "join first"}


def test_second_join_gets_error():
    with client.websocket_connect("/ws") as ws:
        join(ws, "Asha")
        assert join(ws, "Asha again") == {"type": "error", "message": "already joined"}


def test_blank_name_gets_error():
    with client.websocket_connect("/ws") as ws:
        assert join(ws, "   ")["type"] == "error"


def test_server_sets_the_name_not_the_browser():
    with client.websocket_connect("/ws") as ws:
        join(ws, "Asha")
        ws.send_json({"type": "chat", "text": "hi", "name": "Hacker"})
        assert ws.receive_json()["name"] == "Asha"


def test_not_joined_connections_get_no_broadcasts():
    # A connection that hasn't joined isn't "in the room" yet.
    with client.websocket_connect("/ws") as a, client.websocket_connect("/ws") as lurker:
        join(a, "Asha")
        a.send_json({"type": "chat", "text": "hi"})
        a.receive_json()
        # The lurker's next message should be its own pong, not Asha's chat.
        lurker.send_json({"type": "ping"})
        assert lurker.receive_json() == {"type": "pong"}


# ---------- Level 5: catch-up history ----------


def test_newcomer_gets_recent_history():
    with client.websocket_connect("/ws") as a:
        join(a, "Asha")
        for text in ["one", "two", "three"]:
            a.send_json({"type": "chat", "text": text})
            a.receive_json()
        with client.websocket_connect("/ws") as b:
            welcome = join(b, "Ben")
            assert [m["text"] for m in welcome["history"]] == ["one", "two", "three"]
            assert welcome["history"][0]["name"] == "Asha"


def test_history_keeps_only_the_last_n():
    n = settings.history_size
    with client.websocket_connect("/ws") as a:
        join(a, "Asha")
        for i in range(n + 5):
            a.send_json({"type": "chat", "text": f"m{i}"})
            a.receive_json()
        with client.websocket_connect("/ws") as b:
            history = join(b, "Ben")["history"]
            assert len(history) == n
            assert history[0]["text"] == "m5"           # the 5 oldest were dropped
            assert history[-1]["text"] == f"m{n + 4}"   # the newest is last
