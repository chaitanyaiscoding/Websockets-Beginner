from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.chat.manager import manager
from app.chat.schemas import ChatIn, ChatOut, ErrorOut, JoinIn, PingIn, PongOut, client_message
from app.config import settings

router = APIRouter()

# WebSocket close code 1008 = "policy violation": the standard code for
# "you're not allowed to connect".
POLICY_VIOLATION = 1008


@router.websocket("/ws")
async def chat_ws(websocket: WebSocket)->None:
    # 1. Origin check, BEFORE accepting.
    #    Browsers don't apply CORS to WebSockets, so any website could open a
    #    socket to us from a visitor's browser. Browsers always send an Origin
    #    header, so we refuse ones not on our list. No Origin at all means a
    #    non-browser client (tests, command-line tools), which we allow.
    origin = websocket.headers.get("origin")
    if origin is not None and origin not in settings.allowed_origins:
        await websocket.close(code=POLICY_VIOLATION)
        return

    await manager.connect(websocket)
    try:
        while True:
            raw = await websocket.receive_text()

            # 2. Validate. Bad JSON, an unknown type, or a bad field all end up here.
            #    Reply with an error and keep the connection open: one bad
            #    message shouldn't disconnect the user.
            try:
                message = client_message.validate_json(raw)
            except ValidationError as exc:
                problem = exc.errors()[0]["msg"]
                await manager.send(websocket, ErrorOut(message=f"invalid message: {problem}"))
                continue

            # 3. Dispatch on the message's class. Each case pulls out the fields it needs.
            match message:
                case ChatIn(text=text):
                    # The server sets name and sent_at. It never trusts the browser for them.
                    await manager.broadcast(
                        ChatOut(name="anonymous", text=text, sent_at=datetime.now(timezone.utc))
                    )
                case PingIn():
                    # Only the one who asked gets the pong.
                    await manager.send(websocket, PongOut())
                case JoinIn():
                    # Temporary until Level 4 adds names.
                    await manager.send(websocket, ErrorOut(message="join comes in level 4"))
    except WebSocketDisconnect:
        # The client left: stop tracking it, so we never send to a dead socket.
        manager.disconnect(websocket)
