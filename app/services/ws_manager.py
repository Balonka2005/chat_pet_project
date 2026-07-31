import asyncio
import json

from fastapi import WebSocket

from app.db.redis import redis_client


def _channel_name(room_id: int) -> str:
    return f"room:{room_id}"


def _presence_key(room_id: int) -> str:
    return f"room:{room_id}:online"


class ConnectionManager:
    def __init__(self) -> None:
        self._local_connections: dict[int, set[WebSocket]] = {}
        self._listener_tasks: dict[int, asyncio.Task] = {}

    async def connect(self, room_id: int, websocket: WebSocket) -> None:
        await websocket.accept()

        if room_id not in self._local_connections:
            self._local_connections[room_id] = set()
            self._listener_tasks[room_id] = asyncio.create_task(self._listen_to_room(room_id))

        self._local_connections[room_id].add(websocket)

    async def disconnect(self, room_id: int, websocket: WebSocket) -> None:
        connections = self._local_connections.get(room_id)
        if not connections:
            return

        connections.discard(websocket)

        if not connections:
            del self._local_connections[room_id]
            task = self._listener_tasks.pop(room_id, None)
            if task:
                task.cancel()

    async def publish(self, room_id: int, event: dict) -> None:
        await redis_client.publish(_channel_name(room_id), json.dumps(event))

    async def add_online_user(self, room_id: int, user_id: int, username: str) -> None:
        await redis_client.hset(_presence_key(room_id), str(user_id), username)

    async def remove_online_user(self, room_id: int, user_id: int) -> None:
        await redis_client.hdel(_presence_key(room_id), str(user_id))

    async def get_online_users(self, room_id: int) -> list[dict]:
        raw = await redis_client.hgetall(_presence_key(room_id))
        return [{"id": int(uid), "username": username} for uid, username in raw.items()]

    async def _listen_to_room(self, room_id: int) -> None:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(_channel_name(room_id))
        try:
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                await self._broadcast_local(room_id, message["data"])
        except asyncio.CancelledError:
            pass
        finally:
            await pubsub.unsubscribe(_channel_name(room_id))
            await pubsub.close()

    async def _broadcast_local(self, room_id: int, raw_event: str) -> None:
        connections = self._local_connections.get(room_id, set())
        dead: list[WebSocket] = []

        for ws in connections:
            try:
                await ws.send_text(raw_event)
            except Exception:
                dead.append(ws)

        for ws in dead:
            connections.discard(ws)


manager = ConnectionManager()
