import json

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.services import room_service
from app.services.auth_service import get_user_by_id
from app.services.ws_manager import manager

router = APIRouter()


async def _authenticate_ws(token: str):
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    async with AsyncSessionLocal() as db:
        return await get_user_by_id(db, int(user_id))


@router.websocket("/rooms/{room_id}")
async def websocket_chat(websocket: WebSocket, room_id: int, token: str = Query(...)):
    user = await _authenticate_ws(token)
    if user is None:
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as db:
        room = await room_service.get_room_by_id(db, room_id)
    if room is None:
        await websocket.close(code=4404)
        return

    await manager.connect(room_id, websocket)
    await manager.add_online_user(room_id, user.id, user.username)

    async with AsyncSessionLocal() as db:
        history = await room_service.get_room_messages(db, room_id, limit=30, offset=0)

    await websocket.send_text(json.dumps({
        "type": "history",
        "room_id": room_id,
        "messages": [
            {
                "id": m.id,
                "content": m.content,
                "author": {"id": m.author.id, "username": m.author.username},
                "created_at": m.created_at.isoformat(),
            }
            for m in reversed(history)
        ],
    }))

    online_users = await manager.get_online_users(room_id)
    await websocket.send_text(json.dumps({
        "type": "presence",
        "room_id": room_id,
        "online_users": online_users,
    }))

    await manager.publish(room_id, {
        "type": "user_joined",
        "room_id": room_id,
        "user": {"id": user.id, "username": user.username},
        "online_users": online_users,
    })

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
                content = data.get("content", "").strip()
            except json.JSONDecodeError:
                content = raw.strip()

            if not content:
                continue
            if len(content) > 2000:
                content = content[:2000]

            async with AsyncSessionLocal() as db:
                message = await room_service.create_message(db, room_id, user.id, content)

            await manager.publish(room_id, {
                "type": "message",
                "room_id": room_id,
                "message": {
                    "id": message.id,
                    "content": message.content,
                    "author": {"id": user.id, "username": user.username},
                    "created_at": message.created_at.isoformat(),
                },
            })

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(room_id, websocket)
        await manager.remove_online_user(room_id, user.id)
        online_users = await manager.get_online_users(room_id)
        await manager.publish(room_id, {
            "type": "user_left",
            "room_id": room_id,
            "user": {"id": user.id, "username": user.username},
            "online_users": online_users,
        })
