from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_echo():
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello, WebSocket!")
        data = websocket.receive_text()
        assert data == "Message text was: Hello, WebSocket!"