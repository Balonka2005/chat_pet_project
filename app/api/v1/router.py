from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat_ws, rooms, users

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(rooms.router, prefix="/rooms", tags=["rooms"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(chat_ws.router, prefix="/ws", tags=["websocket"])


@api_router.get("/ping", tags=["debug"])
async def ping():
    return {"message": "pong"}
