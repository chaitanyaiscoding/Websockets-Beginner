from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.chat.manager import manager

router = APIRouter()

@router.websocket("/ws")
async def chat_ws(websocket: WebSocket)->None:
    # Level 2: the manager accepts the connection AND starts tracking it.
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Send to everyone, not just back to this one connection.
            await manager.broadcast_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        # The client left: stop tracking it, so we never send to a dead socket.
        manager.disconnect(websocket)
