from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.message import MessageCreate, MessageRead
from app.schemas.room import RoomCreate, RoomRead
from app.services import room_service
from app.services.ws_manager import manager

router = APIRouter()


@router.get("/", response_model=list[RoomRead])
async def get_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await room_service.list_rooms(db)


@router.post("/", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
async def create_room(
    room_in: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if await room_service.get_room_by_name(db, room_in.name):
        raise HTTPException(status_code=400, detail="Комната с таким именем уже существует")
    return await room_service.create_room(db, room_in, creator_id=current_user.id)


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await room_service.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    if room.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Удалить комнату может только её создатель")
    await room_service.delete_room(db, room)


@router.get("/{room_id}/messages", response_model=list[MessageRead])
async def get_room_history(
    room_id: int,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await room_service.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return await room_service.get_room_messages(db, room_id, limit=limit, offset=offset)


@router.get("/{room_id}/online")
async def get_online_users(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await room_service.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return await manager.get_online_users(room_id)


@router.post("/{room_id}/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
async def post_message(
    room_id: int,
    message_in: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    room = await room_service.get_room_by_id(db, room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return await room_service.create_message(db, room_id, current_user.id, message_in.content)
